import secrets

from flask import Blueprint, redirect, render_template, request, session, url_for

from extensions import db
from models import Player, ChatMessage
from room_manager import create_room, get_room, room_exists
from security import validate_player_name
from words import get_word_categories, random_word

lobby_bp = Blueprint("lobby", __name__)


@lobby_bp.route("/")
def index():
    error = session.pop("error", None)
    player_name = session.get("player_name", "")
    return render_template("index.html", phase="home", error=error, player_name=player_name)


@lobby_bp.route("/login", methods=["POST"])
def login():
    player_name = request.form.get("player_name", "").strip()
    if not player_name or not validate_player_name(player_name):
        session["error"] = "Please enter a valid name (letters, numbers, spaces, 1-50 chars)."
        return redirect(url_for("lobby.index"))

    player_token = secrets.token_urlsafe(32)
    session["player_token"] = player_token
    session["player_name"] = player_name
    session.pop("error", None)
    return redirect(url_for("lobby.hub"))


@lobby_bp.route("/hub")
def hub():
    player_token = session.get("player_token")
    player_name = session.get("player_name")
    if not player_token or not player_name:
        return redirect(url_for("lobby.index"))
    error = session.pop("error", None)
    return render_template("index.html", phase="hub", player_name=player_name, player_token=player_token, error=error)


@lobby_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("lobby.index"))


@lobby_bp.route("/room/create", methods=["POST"])
def create_room_route():
    player_name = session.get("player_name")
    player_token = session.get("player_token")
    if not player_name or not player_token:
        return redirect(url_for("lobby.index"))

    if not session.get("_room_secret_word"):
        w = random_word()
        secret_word = w["word"] if w else "secret"
        category = w["category"] if w else "Common"
    else:
        secret_word = session.pop("_room_secret_word", "secret")
        category = session.pop("_room_category", "Common")

    game = create_room(
        player_count=1,
        imposter_count=1,
        jester_count=0,
        jester_info="nothing",
        secret_word=secret_word,
        category=category,
    )

    player = Player(
        game_id=game.game_id,
        player_token=player_token,
        name=player_name,
        color="#7c3aed",
        role="crewmate",
        is_connected=True,
        is_ready=False,
    )
    db.session.add(player)
    db.session.commit()

    game.creator_player_id = player.player_id
    game.num_players = 1
    db.session.commit()

    session["room_code"] = game.room_code
    return redirect(url_for("lobby.room_page", room_code=game.room_code))


@lobby_bp.route("/room/join", methods=["POST"])
def join_room_route():
    room_code = request.form.get("room_code", "").strip().upper()
    player_name = session.get("player_name", "").strip()

    if not room_exists(room_code):
        session["error"] = "Room not found."
        return redirect(url_for("lobby.hub"))

    if not validate_player_name(player_name):
        session["error"] = "Please enter a valid name."
        return redirect(url_for("lobby.hub"))

    game = get_room(room_code)

    existing = Player.query.filter_by(game_id=game.game_id, name=player_name).first()
    if existing:
        session["error"] = f"The name '{player_name}' is already taken."
        return redirect(url_for("lobby.room_page", room_code=room_code))

    player_token = secrets.token_urlsafe(32)
    player = Player(
        game_id=game.game_id,
        player_token=player_token,
        name=player_name,
        color="#10b981",
        role="crewmate",
        is_connected=True,
        is_ready=False,
    )
    db.session.add(player)
    game.num_players = Player.query.filter_by(game_id=game.game_id).count()
    db.session.commit()

    session["room_code"] = room_code
    session["player_token"] = player_token
    session["player_name"] = player_name

    return redirect(url_for("lobby.room_page", room_code=room_code))


@lobby_bp.route("/room/<room_code>")
def room_page(room_code):
    game = get_room(room_code)
    if not game:
        return redirect(url_for("lobby.index"))

    player_token = session.get("player_token")
    current_player = None
    if player_token:
        current_player = Player.query.filter_by(game_id=game.game_id, player_token=player_token).first()

    players = Player.query.filter_by(game_id=game.game_id).order_by(Player.player_id).all()
    messages = ChatMessage.query.filter_by(game_id=game.game_id).order_by(ChatMessage.timestamp).all()

    if game.phase in ("role_reveal",) and current_player:
        player_index = next((i for i, p in enumerate(players) if p.player_id == current_player.player_id), 0)
        return render_template("index.html",
            phase="role_reveal",
            game=game, room_code=room_code,
            players=players, current_player=current_player,
            current_player_index=player_index)

    if game.phase in ("clue", "vote") and current_player:
        clues = {r.player_id: r.clue_given for r in game.rounds if r.round_number == game.round_number}
        return render_template("index.html",
            phase="game",
            game=game, room_code=room_code,
            players=players, current_player=current_player,
            clues=clues, messages=messages)

    if game.status == "finished" and current_player:
        return render_template("index.html",
            phase="game",
            game=game, room_code=room_code,
            players=players, current_player=current_player,
            messages=messages)

    error = session.pop("error", None)
    return render_template("index.html",
        phase="lobby",
        game=game, room_code=room_code,
        players=players, current_player=current_player,
        messages=messages, error=error,
        word_categories=get_word_categories())
