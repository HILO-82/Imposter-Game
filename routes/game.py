import secrets

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from extensions import db
from game_logic import (
    all_clues_submitted,
    alive_players,
    check_win_condition,
    create_game_from_setup,
    eliminate_top_voted,
    tally_votes,
)
from ml.vote_bot import bot_vote
from ml.word_bot import bot_guess
from models import Game, Player, Round, Vote
from room_manager import generate_room_code
from security import game_session_required, validate_clue, validate_player_name, validate_positive_int
from words import get_word_categories, random_word

game_bp = Blueprint("game", __name__)


# ── Single Device (pass-and-play) routes ──

@game_bp.route("/game/setup", methods=["GET"])
def setup_form():
    from routes.settings import get_or_create_settings
    s = get_or_create_settings()
    categories = get_word_categories()
    return render_template("setup.html", categories=categories, defaults=s)


@game_bp.route("/game/setup", methods=["POST"])
def create_local_game():
    names = request.form.getlist("player_name")
    names = [n.strip() for n in names if n.strip()]
    if len(names) < 3:
        from routes.settings import get_or_create_settings
        categories = get_word_categories()
        return render_template("setup.html", error="At least 3 players required", categories=categories, defaults=get_or_create_settings())
    if len(names) > 8:
        from routes.settings import get_or_create_settings
        categories = get_word_categories()
        return render_template("setup.html", error="Maximum 8 players", categories=categories, defaults=get_or_create_settings())

    imposter_count = int(request.form.get("imposter_count", 1))
    jester_count = int(request.form.get("jester_count", 0))
    jester_info = request.form.get("jester_info", "nothing")
    category = request.form.get("category", "Animals")
    secret_word = request.form.get("secret_word", "").strip()

    setup = {
        "players": [{"name": n} for n in names],
        "imposter_count": imposter_count,
        "jester_count": jester_count,
        "jester_info": jester_info,
        "word_category": category,
        "secret_word": secret_word or None,
    }
    game = create_game_from_setup(setup)
    session["game_id"] = game.game_id
    session.modified = True
    return redirect(url_for("game.reveal_roles", game_id=game.game_id))


@game_bp.route("/game/<int:game_id>")
@game_session_required
def view_game(game_id):
    game = Game.query.get_or_404(game_id)
    players = Player.query.filter_by(game_id=game_id).order_by(Player.player_id).all()
    clues = Round.query.filter_by(game_id=game_id, round_number=game.round_number).all()
    clue_map = {c.player_id: c.clue_given for c in clues}
    return render_template(
        "game.html",
        game=game,
        players=players,
        clues=clue_map,
        alive=alive_players(game_id),
    )


@game_bp.route("/game/<int:game_id>/clue", methods=["POST"])
@game_session_required
def submit_clue(game_id):
    game = Game.query.get_or_404(game_id)
    player_id = request.form.get("player_id", type=int)
    clue = request.form.get("clue", "").strip()

    if not validate_positive_int(player_id, 1, 99999):
        return redirect(url_for("game.view_game", game_id=game_id))

    if not validate_clue(clue):
        return redirect(url_for("game.view_game", game_id=game_id))

    player = Player.query.filter_by(player_id=player_id, game_id=game_id).first()
    if not player or player.was_voted_out or player.is_bot:
        return redirect(url_for("game.view_game", game_id=game_id))

    existing = Round.query.filter_by(
        game_id=game_id,
        round_number=game.round_number,
        player_id=player_id,
    ).first()
    if existing:
        existing.clue_given = clue
    else:
        db.session.add(
            Round(
                game_id=game_id,
                round_number=game.round_number,
                clue_given=clue,
                player_id=player_id,
            )
        )
    db.session.commit()

    if all_clues_submitted(game):
        game.phase = "vote"
        db.session.commit()
    return redirect(url_for("game.view_game", game_id=game_id))


@game_bp.route("/game/<int:game_id>/vote", methods=["POST"])
@game_session_required
def submit_vote(game_id):
    game = Game.query.get_or_404(game_id)
    voter_id = request.form.get("voter_id", type=int)
    target_id = request.form.get("target_id", type=int)

    if not validate_positive_int(voter_id) or not validate_positive_int(target_id):
        return redirect(url_for("game.view_game", game_id=game_id))

    voter = Player.query.filter_by(player_id=voter_id, game_id=game_id).first()
    target = Player.query.filter_by(player_id=target_id, game_id=game_id).first()
    if not voter or not target or voter.was_voted_out or target.was_voted_out:
        return redirect(url_for("game.view_game", game_id=game_id))

    db.session.add(
        Vote(
            game_id=game_id,
            round_number=game.round_number,
            voter_id=voter_id,
            target_id=target_id,
        )
    )
    db.session.commit()

    _bot_cast_vote(game)
    eliminate_top_voted(game)
    winner = check_win_condition(game)

    if winner:
        game.winning_role = winner
        game.status = "finished"
        db.session.commit()
        return redirect(url_for("game.result", game_id=game_id))

    game.round_number += 1
    game.phase = "clue"
    db.session.commit()
    return redirect(url_for("game.view_game", game_id=game_id))


def _bot_cast_vote(game):
    bot = Player.query.filter_by(game_id=game.game_id, is_bot=True).first()
    if not bot or bot.was_voted_out:
        return

    players = Player.query.filter_by(game_id=game.game_id).all()
    clues = Round.query.filter_by(game_id=game.game_id, round_number=game.round_number).all()
    vote_rows = Vote.query.filter_by(game_id=game.game_id).all()
    vote_counts = {}
    for v in vote_rows:
        vote_counts[v.target_id] = vote_counts.get(v.target_id, 0) + 1

    state = {
        "players": [
            {
                "player_id": p.player_id,
                "role": p.role,
                "was_voted_out": p.was_voted_out,
                "is_bot": p.is_bot,
            }
            for p in players
        ],
        "round_number": game.round_number,
        "vote_counts": vote_counts,
        "clues": {c.player_id: c.clue_given for c in clues},
        "secret_word": game.secret_word,
        "bot_role": bot.role,
    }
    target_id = bot_vote(state)
    if not target_id:
        return

    db.session.add(
        Vote(
            game_id=game.game_id,
            round_number=game.round_number,
            voter_id=bot.player_id,
            target_id=target_id,
        )
    )
    db.session.commit()


@game_bp.route("/bot/guess", methods=["POST"])
def bot_guess_route():
    if request.is_json:
        data = request.get_json(silent=True) or {}
        clues = data.get("clues", [])
        category = data.get("category")
    else:
        clues = request.form.getlist("clues") or [request.form.get("clues", "")]
        category = request.form.get("category")
    if isinstance(clues, str):
        clues = [clues]
    guess = bot_guess(clues, secret_category=category)
    return jsonify({"guess": guess})


@game_bp.route("/game/<int:game_id>/result")
@game_session_required
def result(game_id):
    game = Game.query.get_or_404(game_id)
    players = Player.query.filter_by(game_id=game_id).all()
    bot_guess_word = None
    bot = Player.query.filter_by(game_id=game_id, is_bot=True).first()
    if bot:
        all_clues = Round.query.filter_by(game_id=game_id).all()
        clue_texts = [r.clue_given for r in all_clues]
        bot_guess_word = bot_guess(clue_texts, secret_category=game.category)
    return render_template(
        "result.html",
        game=game,
        players=players,
        bot_guess_word=bot_guess_word,
    )


@game_bp.route("/game/<int:game_id>/roles")
@game_session_required
def reveal_roles(game_id):
    game = Game.query.get_or_404(game_id)
    players = Player.query.filter_by(game_id=game_id).order_by(Player.player_id).all()
    players_data = [{"name": p.name, "role": p.role, "player_id": p.player_id} for p in players]
    return render_template("reveal.html", game=game, players=players_data)


@game_bp.route("/game/<int:game_id>/start-play", methods=["POST"])
@game_session_required
def start_play(game_id):
    game = Game.query.get_or_404(game_id)
    game.phase = "clue"
    db.session.commit()
    return redirect(url_for("game.view_game", game_id=game_id))


# ── Multi Device routes ──

@game_bp.route("/multi-device/host", methods=["GET"])
def multi_host_setup():
    from routes.settings import get_or_create_settings
    s = get_or_create_settings()
    categories = get_word_categories()
    return render_template("multi_setup.html", categories=categories, defaults=s)


@game_bp.route("/multi-device/host", methods=["POST"])
def multi_host_create():
    names_raw = request.form.getlist("player_name")
    names = [n.strip() for n in names_raw if n.strip()]
    if len(names) < 3:
        from routes.settings import get_or_create_settings
        s = get_or_create_settings()
        categories = get_word_categories()
        return render_template("multi_setup.html", error="At least 3 players required", categories=categories, defaults=s)
    if len(names) > 8:
        from routes.settings import get_or_create_settings
        s = get_or_create_settings()
        categories = get_word_categories()
        return render_template("multi_setup.html", error="Maximum 8 players", categories=categories, defaults=s)

    imposter_count = int(request.form.get("imposter_count", 1))
    jester_count = int(request.form.get("jester_count", 0))
    jester_info = request.form.get("jester_info", "nothing")
    category = request.form.get("category", "Animals")
    secret_word = request.form.get("secret_word", "").strip()

    from game_logic import assign_roles

    code = generate_room_code()
    host_token = secrets.token_urlsafe(32)
    word_obj = random_word(category) if not secret_word else None
    final_word = secret_word or word_obj["word"]

    game = Game(
        room_code=code,
        num_players=len(names),
        imposter_count=imposter_count,
        jester_count=jester_count,
        jester_info=jester_info,
        secret_word=final_word,
        category=category,
        status="lobby",
        phase="lobby",
        round_number=1,
        is_multi_device=True,
        host_token=host_token,
    )
    db.session.add(game)
    db.session.flush()

    players_data = [{"name": n, "role": "crewmate"} for n in names]
    assigned = assign_roles(players_data, imposter_count, jester_count)
    player_list = []
    for i, p in enumerate(assigned):
        player = Player(
            game_id=game.game_id,
            player_token=None,
            name=p["name"],
            role=p["role"],
            color=["#7c3aed", "#10b981", "#f59e0b", "#ef4444", "#3b82f6", "#ec4899", "#14b8a6", "#f97316"][i % 8],
        )
        db.session.add(player)
        db.session.flush()
        player_list.append(player)

    game.creator_player_id = player_list[0].player_id
    db.session.commit()

    session["host_token"] = host_token
    session["game_id"] = game.game_id
    session.modified = True

    return redirect(url_for("game.multi_host_dashboard", game_id=game.game_id))


@game_bp.route("/multi-device/dashboard/<int:game_id>")
def multi_host_dashboard(game_id):
    game = Game.query.get_or_404(game_id)
    host_token = session.get("host_token")
    if not host_token or game.host_token != host_token:
        return redirect(url_for("lobby.index"))

    players = Player.query.filter_by(game_id=game_id).order_by(Player.player_id).all()
    clues = Round.query.filter_by(game_id=game_id, round_number=game.round_number).all()

    host_url = request.host_url.rstrip("/")
    join_url = f"{host_url}/multi-device/join/{game.room_code}"

    return render_template("multi_host.html",
        game=game,
        players=players,
        clues=clues,
        join_url=join_url,
        host_token=host_token)


@game_bp.route("/multi-device/join/<code>", methods=["GET"])
def multi_join(code):
    game = Game.query.filter_by(room_code=code, is_multi_device=True).first()
    if not game:
        return render_template("error.html", code=404, message="Game not found.")

    if game.status != "lobby":
        return redirect(url_for("game.multi_play", code=code, token=request.args.get("token", "")))

    error = request.args.get("error", "")
    player_count = Player.query.filter_by(game_id=game.game_id).count()
    max_players = Player.query.filter_by(game_id=game.game_id).count()  # fixed by initial setup
    return render_template("multi_join.html", game=game, error=error, code=code)


@game_bp.route("/multi-device/join/<code>", methods=["POST"])
def multi_join_post(code):
    game = Game.query.filter_by(room_code=code, is_multi_device=True).first()
    if not game or game.status != "lobby":
        return redirect(url_for("lobby.index"))

    name = request.form.get("name", "").strip()
    if not validate_player_name(name):
        return redirect(url_for("game.multi_join", code=code, error="Please enter a valid name."))

    existing = Player.query.filter_by(game_id=game.game_id, name=name).first()
    if existing:
        return redirect(url_for("game.multi_join", code=code, error=f"Name '{name}' is already taken."))

    unassigned = Player.query.filter_by(game_id=game.game_id, player_token=None).first()
    if not unassigned:
        return redirect(url_for("game.multi_join", code=code, error="Game is full."))

    player_token = secrets.token_urlsafe(32)
    unassigned.name = name
    unassigned.player_token = player_token
    unassigned.session_id = player_token
    db.session.commit()

    return redirect(url_for("game.multi_play", code=code, token=player_token))


@game_bp.route("/multi-device/play/<code>")
def multi_play(code):
    game = Game.query.filter_by(room_code=code, is_multi_device=True).first()
    if not game:
        return render_template("error.html", code=404, message="Game not found.")

    token = request.args.get("token", "")
    player = Player.query.filter_by(game_id=game.game_id, player_token=token).first()
    if not player:
        return redirect(url_for("game.multi_join", code=code))

    clues = Round.query.filter_by(game_id=game.game_id, round_number=game.round_number).all()
    clue_map = {c.player_id: c.clue_given for c in clues}
    votes_this_round = Vote.query.filter_by(game_id=game.game_id, round_number=game.round_number).all()

    return render_template("multi_player.html",
        game=game,
        player=player,
        clues=clue_map,
        votes=votes_this_round,
        players=Player.query.filter_by(game_id=game.game_id).all(),
        code=code)
