from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from extensions import db
from game_logic import (
    all_clues_submitted,
    alive_players,
    check_win_condition,
    create_game_from_setup,
    eliminate_top_voted,
)
from ml.vote_bot import bot_vote
from ml.word_bot import bot_guess
from models import Game, Player, Round, Vote
from security import game_session_required, validate_clue, validate_positive_int

game_bp = Blueprint("game", __name__)


@game_bp.route("/game/new", methods=["POST"])
def new_game():
    setup = session.get("setup")
    if not setup or not setup.get("players"):
        return redirect(url_for("lobby.index"))
    game = create_game_from_setup(setup, include_bot=True)
    session["game_id"] = game.game_id
    session.modified = True
    return redirect(url_for("game.view_game", game_id=game.game_id))


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

    round_row = Round.query.filter_by(
        game_id=game_id, round_number=game.round_number
    ).first()
    round_id = round_row.round_id if round_row else None

    db.session.add(
        Vote(
            game_id=game_id,
            round_id=round_id,
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
    """Logistic regression bot votes after human vote."""
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

    round_row = Round.query.filter_by(
        game_id=game.game_id, round_number=game.round_number
    ).first()
    db.session.add(
        Vote(
            game_id=game.game_id,
            round_id=round_row.round_id if round_row else None,
            voter_id=bot.player_id,
            target_id=target_id,
        )
    )
    db.session.commit()


@game_bp.route("/bot/guess", methods=["POST"])
def bot_guess_route():
    """KNN endpoint: guess secret word from clues JSON body or form."""
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


@game_bp.route("/game/<int:game_id>/start-play", methods=["POST"])
@game_session_required
def start_play(game_id):
    """After role reveal, begin clue/vote rounds."""
    return redirect(url_for("game.view_game", game_id=game_id))
