from flask import Blueprint, redirect, render_template, request, session, url_for
import secrets

from extensions import db, socketio
from game_logic import assign_roles, default_setup_state
from models import Player
from room_manager import create_room, get_room, room_exists
from security import validate_player_name
from words import get_word_categories, random_word

lobby_bp = Blueprint("lobby", __name__)


def get_setup():
    if "setup" not in session:
        session["setup"] = default_setup_state()
    setup = session["setup"]
    if "role_revealed" not in setup:
        setup["role_revealed"] = False
        session["setup"] = setup
        session.modified = True
    return setup


def save_setup(setup):
    session["setup"] = setup
    session.modified = True


def _save_player_inputs_from_form(setup):
    """Keep typed names/colors when navigating setup actions."""
    saved = {}
    for i in range(1, setup["player_count"] + 1):
        saved[str(i)] = {
            "name": request.form.get(f"player{i}", "").strip(),
            "color": request.form.get(f"color{i}", "#ff0000"),
        }
    setup["saved_player_inputs"] = saved


def _validate_player_token(player_token):
    if session.get("player_token") != player_token:
        return None
    player_name = session.get("player_name")
    return player_name if player_name else None


@lobby_bp.route("/")
def index():
    """Home page: simple name entry form."""
    error = session.pop("error", None)
    return render_template(
        "index.html",
        phase="home",
        error=error,
    )


@lobby_bp.route("/login", methods=["POST"])
def login():
    """Create a unique player session and redirect to their personal hub."""
    player_name = request.form.get("player_name", "").strip()
    
    if not player_name or not validate_player_name(player_name):
        session["error"] = "Please enter a valid name."
        return redirect(url_for("lobby.index"))

    # Create a unique player token for this session
    player_token = secrets.token_urlsafe(32)
    session["player_token"] = player_token
    session["player_name"] = player_name
    session.modified = True
    session.pop("error", None)
    
    return redirect(url_for("lobby.player_hub", player_token=player_token))


@lobby_bp.route("/player/<player_token>")
def player_hub(player_token):
    """Main hub for a player: shows all game options."""
    player_name = _validate_player_token(player_token)
    if not player_name:
        return redirect(url_for("lobby.index"))
    
    setup = get_setup()
    setup["phase"] = "welcome"
    save_setup(setup)
    
    error = session.pop("error", None)
    return render_template(
        "index.html",
        phase="player_hub",
        game_state=setup,
        player_name=player_name,
        player_token=player_token,
        word_categories=get_word_categories(),
        error=error,
    )


@lobby_bp.route("/player/<player_token>/settings")
def player_settings(player_token):
    player_name = _validate_player_token(player_token)
    if not player_name:
        return redirect(url_for("lobby.index"))

    setup = get_setup()
    setup["phase"] = "settings"
    save_setup(setup)
    error = session.pop("error", None)
    return render_template(
        "index.html",
        phase="settings",
        game_state=setup,
        word_categories=get_word_categories(),
        player_token=player_token,
        error=error,
    )


@lobby_bp.route("/player/<player_token>/settings", methods=["POST"])
def player_save_settings(player_token):
    player_name = _validate_player_token(player_token)
    if not player_name:
        return redirect(url_for("lobby.index"))

    setup = get_setup()
    setup["player_count"] = int(request.form.get("player_count", 6))
    setup["imposter_count"] = int(request.form.get("imposter_count", 1))
    setup["jester_count"] = int(request.form.get("jester_count", 0))
    setup["jester_info"] = request.form.get("jester_info", "nothing")
    setup["word_category"] = request.form.get("word_category", "Animals")
    secret = request.form.get("secret_word", "").strip()
    if secret:
        setup["secret_word"] = secret
    elif not setup.get("secret_word"):
        w = random_word(setup["word_category"])
        setup["secret_word"] = w["word"] if w else "cat"
    save_setup(setup)
    return redirect(url_for("lobby.player_hub", player_token=player_token))


@lobby_bp.route("/player/<player_token>/generate-word")
def player_generate_random_word(player_token):
    player_name = _validate_player_token(player_token)
    if not player_name:
        return redirect(url_for("lobby.index"))

    setup = get_setup()
    w = random_word(setup.get("word_category"))
    if w:
        setup["secret_word"] = w["word"]
        setup["word_category"] = w["category"]
    save_setup(setup)
    return redirect(url_for("lobby.player_settings", player_token=player_token))


@lobby_bp.route("/player/<player_token>/start")
def player_start_game(player_token):
    player_name = _validate_player_token(player_token)
    if not player_name:
        return redirect(url_for("lobby.index"))

    setup = get_setup()
    if not setup.get("secret_word"):
        w = random_word(setup.get("word_category"))
        setup["secret_word"] = w["word"] if w else "cat"
        setup["word_category"] = w["category"] if w else "Animals"
    setup["phase"] = "setup"
    save_setup(setup)
    return render_template(
        "index.html",
        phase="setup",
        game_state=setup,
        word_categories=get_word_categories(),
        player_token=player_token,
        player_name=player_name,
    )


@lobby_bp.route("/logout", methods=["POST"])
def logout():
    """Log out the current player."""
    session.clear()
    return redirect(url_for("lobby.index"))


@lobby_bp.route("/settings")
def settings():
    setup = get_setup()
    setup["phase"] = "settings"
    save_setup(setup)
    return render_template(
        "index.html",
        phase="settings",
        game_state=setup,
        word_categories=get_word_categories(),
    )


@lobby_bp.route("/settings", methods=["POST"])
def save_settings():
    setup = get_setup()
    setup["player_count"] = int(request.form.get("player_count", 6))
    setup["imposter_count"] = int(request.form.get("imposter_count", 1))
    setup["jester_count"] = int(request.form.get("jester_count", 0))
    setup["jester_info"] = request.form.get("jester_info", "nothing")
    setup["word_category"] = request.form.get("word_category", "Animals")
    secret = request.form.get("secret_word", "").strip()
    if secret:
        setup["secret_word"] = secret
    elif not setup.get("secret_word"):
        w = random_word(setup["word_category"])
        setup["secret_word"] = w["word"] if w else "cat"
    save_setup(setup)
    return redirect(url_for("lobby.index"))


@lobby_bp.route("/generate-word")
def generate_random_word():
    setup = get_setup()
    w = random_word(setup.get("word_category"))
    if w:
        setup["secret_word"] = w["word"]
        setup["word_category"] = w["category"]
    save_setup(setup)
    return redirect(url_for("lobby.settings"))


@lobby_bp.route("/start")
def start_game():
    setup = get_setup()
    if not setup.get("secret_word"):
        w = random_word(setup.get("word_category"))
        setup["secret_word"] = w["word"] if w else "cat"
        setup["word_category"] = w["category"] if w else "Animals"
    setup["phase"] = "setup"
    save_setup(setup)
    return render_template(
        "index.html",
        phase="setup",
        game_state=setup,
        word_categories=get_word_categories(),
    )


@lobby_bp.route("/assign-roles", methods=["POST"])
def assign_roles_route():
    setup = get_setup()
    _save_player_inputs_from_form(setup)
    count = setup["player_count"]
    players = []
    for i in range(1, count + 1):
        name = request.form.get(f"player{i}", f"Player {i}").strip()
        if not validate_player_name(name):
            name = f"Player {i}"
        color = request.form.get(f"color{i}", "#ff0000")
        players.append({"name": name, "color": color, "role": "crewmate", "is_bot": False})
    if setup.get("has_ai_bot"):
        players.append(
            {"name": "AI Bot", "color": "#333333", "role": "crewmate", "is_bot": True}
        )
    players = assign_roles(players, setup["imposter_count"], setup["jester_count"])
    setup["players"] = players
    setup["current_player_index"] = 0
    setup["role_revealed"] = False
    setup["phase"] = "role_reveal"
    save_setup(setup)
    player_token = session.get("player_token")
    return render_template(
        "index.html",
        phase="role_reveal",
        game_state=setup,
        word_categories=get_word_categories(),
        player_token=player_token,
    )


@lobby_bp.route("/player/<player_token>/assign-roles", methods=["POST"])
def player_assign_roles_route(player_token):
    player_name = _validate_player_token(player_token)
    if not player_name:
        return redirect(url_for("lobby.index"))
    return assign_roles_route()


@lobby_bp.route("/reveal-role")
def reveal_role():
    setup = get_setup()
    setup["phase"] = "role_reveal"
    setup["role_revealed"] = True
    save_setup(setup)
    player_token = session.get("player_token")
    return render_template(
        "index.html",
        phase="role_reveal",
        game_state=setup,
        word_categories=get_word_categories(),
        player_token=player_token,
    )


@lobby_bp.route("/player/<player_token>/reveal-role")
def player_reveal_role(player_token):
    player_name = _validate_player_token(player_token)
    if not player_name:
        return redirect(url_for("lobby.index"))
    return reveal_role()


@lobby_bp.route("/next-player")
def next_player():
    setup = get_setup()
    setup["current_player_index"] = setup.get("current_player_index", 0) + 1
    setup["role_revealed"] = False
    save_setup(setup)
    player_token = session.get("player_token")
    return render_template(
        "index.html",
        phase="role_reveal",
        game_state=setup,
        word_categories=get_word_categories(),
        player_token=player_token,
    )


@lobby_bp.route("/player/<player_token>/next-player")
def player_next_player(player_token):
    player_name = _validate_player_token(player_token)
    if not player_name:
        return redirect(url_for("lobby.index"))
    return next_player()


@lobby_bp.route("/play-again")
def play_again():
    setup = get_setup()
    w = random_word(setup.get("word_category"))
    if w:
        setup["secret_word"] = w["word"]
        setup["word_category"] = w["category"]
    if setup.get("players"):
        players = [
            {
                "name": p["name"],
                "color": p.get("color", "#ff0000"),
                "role": "crewmate",
                "is_bot": p.get("is_bot", False),
            }
            for p in setup["players"]
        ]
        setup["players"] = assign_roles(
            players, setup["imposter_count"], setup["jester_count"]
        )
    setup["current_player_index"] = 0
    setup["role_revealed"] = False
    setup["phase"] = "role_reveal"
    save_setup(setup)
    player_token = session.get("player_token")
    return render_template(
        "index.html",
        phase="role_reveal",
        game_state=setup,
        word_categories=get_word_categories(),
        player_token=player_token,
    )


@lobby_bp.route("/player/<player_token>/play-again")
def player_play_again(player_token):
    player_name = _validate_player_token(player_token)
    if not player_name:
        return redirect(url_for("lobby.index"))
    return play_again()


@lobby_bp.route("/add-ai-bot", methods=["POST"])
def add_ai_bot():
    setup = get_setup()
    _save_player_inputs_from_form(setup)
    setup["has_ai_bot"] = True
    setup["phase"] = "setup"
    save_setup(setup)
    return render_template(
        "index.html",
        phase="setup",
        game_state=setup,
        word_categories=get_word_categories(),
    )


@lobby_bp.route("/remove-ai-bot", methods=["POST"])
def remove_ai_bot():
    setup = get_setup()
    _save_player_inputs_from_form(setup)
    setup["has_ai_bot"] = False
    setup["phase"] = "setup"
    save_setup(setup)
    return render_template(
        "index.html",
        phase="setup",
        game_state=setup,
        word_categories=get_word_categories(),
    )


@lobby_bp.route("/create-room", methods=["POST"])
def create_room_route():
    """Create a new game room and redirect to it."""
    player_name = session.get("player_name")
    
    if not player_name:
        return redirect(url_for("lobby.index"))
    
    setup = get_setup()
    
    # Generate secret word if not set
    if not setup.get("secret_word"):
        w = random_word(setup.get("word_category"))
        setup["secret_word"] = w["word"] if w else "cat"
        setup["word_category"] = w["category"] if w else "Animals"
    
    game = create_room(
        player_count=setup["player_count"],
        imposter_count=setup["imposter_count"],
        jester_count=setup["jester_count"],
        jester_info=setup["jester_info"],
        secret_word=setup["secret_word"],
        category=setup["word_category"]
    )
    
    # Create the creator as the first player using logged-in name
    player_token = secrets.token_urlsafe(32)
    player = Player(
        game_id=game.game_id,
        session_id=secrets.token_hex(16),
        player_token=player_token,
        name=player_name,
        color="#ff0000",
        role="crewmate",
        is_connected=True,
        is_ready=False
    )
    db.session.add(player)
    db.session.commit()
    
    # Set the creator
    game.creator_player_id = player.player_id
    db.session.commit()
    
    session["room_code"] = game.room_code
    session["player_token"] = player_token
    
    return redirect(url_for("lobby.player_room", room_code=game.room_code, player_token=player_token))


@lobby_bp.route("/join-room", methods=["POST"])
def join_room_route():
    """Join an existing game room."""
    room_code = request.form.get("room_code", "").strip().upper()
    
    if not room_exists(room_code):
        return redirect(url_for("lobby.index"))
    
    # Clear any stale player token from a previous room so a new join starts cleanly.
    session.pop("player_token", None)
    session["room_code"] = room_code
    # Redirect to the generic room page where players can join with their name
    return redirect(url_for("lobby.room", room_code=room_code))


@lobby_bp.route("/room/<room_code>")
def room(room_code):
    """Display the game room lobby or game phase."""
    game = get_room(room_code)
    
    if not game:
        return redirect(url_for("lobby.index"))
    
    players = Player.query.filter_by(game_id=game.game_id).all()
    current_player = None
    current_player_token = session.get("player_token")
    if current_player_token:
        current_player = Player.query.filter_by(
            game_id=game.game_id,
            player_token=current_player_token,
        ).first()
        if not current_player:
            session.pop("player_token", None)
            session.modified = True

    error = session.pop("error", None)

    if game.phase == "game":
        from models import Round
        # Get existing clues for the current round
        existing_clues = Round.query.filter_by(
            game_id=game.game_id,
            round_number=game.round_number
        ).all()
        
        return render_template(
            "index.html",
            phase="game",
            game=game,
            room_code=room_code,
            players=players,
            current_player=current_player,
            existing_clues=existing_clues,
            word_categories=get_word_categories(),
        )
    
    return render_template(
        "index.html",
        phase="room_lobby",
        game=game,
        room_code=room_code,
        players=players,
        current_player=current_player,
        error=error,
        word_categories=get_word_categories(),
    )


@lobby_bp.route("/room/<room_code>/player/<player_token>")
def player_room(room_code, player_token):
    """Display the game room lobby or game phase for a specific player."""
    game = get_room(room_code)
    
    if not game:
        return redirect(url_for("lobby.index"))
    
    # Get the current player by token
    current_player = Player.query.filter_by(
        game_id=game.game_id,
        player_token=player_token
    ).first()

    if not current_player:
        return redirect(url_for("lobby.index"))

    error = session.pop("error", None)

    # Update session
    session["room_code"] = room_code
    session["player_name"] = current_player.name
    session["player_token"] = player_token
    
    players = Player.query.filter_by(game_id=game.game_id).all()
    
    if game.phase == "game":
        from models import Round
        # Get existing clues for the current round
        existing_clues = Round.query.filter_by(
            game_id=game.game_id,
            round_number=game.round_number
        ).all()
        
        return render_template(
            "index.html",
            phase="game",
            game=game,
            room_code=room_code,
            players=players,
            current_player=current_player,
            existing_clues=existing_clues,
            word_categories=get_word_categories(),
        )
    
    return render_template(
        "index.html",
        phase="room_lobby",
        game=game,
        room_code=room_code,
        players=players,
        current_player=current_player,
        error=error,
        word_categories=get_word_categories(),
    )


@lobby_bp.route("/join-game", methods=["POST"])
def join_game():
    """Join a game room as a player."""
    room_code = request.form.get("room_code", "").strip().upper()
    player_name = request.form.get("player_name", "").strip()
    player_color = request.form.get("player_color", "#ff0000")
    
    if not room_exists(room_code):
        return redirect(url_for("lobby.index"))
    
    # Use logged-in name if provided, otherwise use form input
    if not player_name:
        player_name = session.get("player_name", "").strip()
    
    if not validate_player_name(player_name):
        return redirect(url_for("lobby.room", room_code=room_code))

    game = get_room(room_code)
    current_player_token = session.get("player_token")

    # Check if this name already exists in the room
    existing_player = Player.query.filter_by(
        game_id=game.game_id,
        name=player_name
    ).first()

    if existing_player:
        if current_player_token and existing_player.player_token == current_player_token:
            return redirect(url_for("lobby.player_room", room_code=room_code, player_token=current_player_token))

        session["error"] = f"The name '{player_name}' is already taken in this room."
        return redirect(url_for("lobby.room", room_code=room_code))

    # Create new player with unique token
    player_token = secrets.token_urlsafe(32)
    player = Player(
        game_id=game.game_id,
        session_id=secrets.token_hex(16),
        player_token=player_token,
        name=player_name,
        color=player_color,
        role="crewmate",
        is_connected=True
    )
    db.session.add(player)
    db.session.commit()
    
    session["room_code"] = room_code
    session["player_name"] = player_name
    session["player_token"] = player_token
    
    # Clear any previous error
    session.pop("error", None)
    
    # Emit socket event for real-time update (will be handled by client-side polling)
    # The client will automatically reload when it detects new players
    
    return redirect(url_for("lobby.player_room", room_code=room_code, player_token=player_token))


@lobby_bp.route("/add-ai-bot-room", methods=["POST"])
def add_ai_bot_room():
    """Add an AI bot to the current room."""
    room_code = request.form.get("room_code", "").strip().upper()
    player_token = session.get("player_token")
    
    if not room_exists(room_code):
        return redirect(url_for("lobby.index"))
    
    game = get_room(room_code)
    
    # Create AI bot player
    bot = Player(
        game_id=game.game_id,
        session_id=None,
        name=f"AI Bot {Player.query.filter_by(game_id=game.game_id).count() + 1}",
        color="#333333",
        role="crewmate",
        is_bot=True,
        is_connected=True,
        is_ready=True
    )
    db.session.add(bot)
    game.num_players += 1
    db.session.commit()
    
    return redirect(url_for("lobby.player_room", room_code=room_code, player_token=player_token))


@lobby_bp.route("/start-multiplayer-game", methods=["POST"])
def start_multiplayer_game():
    """Start the multiplayer game and assign roles."""
    room_code = request.form.get("room_code", "").strip().upper()
    requested_token = request.form.get("player_token")
    session_token = session.get("player_token")
    
    if not room_exists(room_code):
        return redirect(url_for("lobby.index"))

    game = get_room(room_code)
    creator = Player.query.filter_by(
        game_id=game.game_id,
        player_id=game.creator_player_id
    ).first()

    if not creator:
        return redirect(url_for("lobby.index"))

    player_token = requested_token or session_token or creator.player_token
    current_player = Player.query.filter_by(
        game_id=game.game_id,
        player_token=player_token
    ).first()

    # Check if current player is the creator
    if not current_player or current_player.player_id != game.creator_player_id:
        return redirect(url_for("lobby.room", room_code=room_code))
    
    players = Player.query.filter_by(game_id=game.game_id).all()
    
    if len(players) < game.num_players:
        return redirect(url_for("lobby.player_room", room_code=room_code, player_token=player_token))
    
    # Assign roles using the existing assign_roles function
    player_data = [
        {"name": p.name, "color": p.color, "role": "crewmate", "is_bot": p.is_bot}
        for p in players
    ]
    assigned_players = assign_roles(player_data, game.imposter_count, game.jester_count)
    
    # Update players in database with assigned roles
    for i, player in enumerate(players):
        player.role = assigned_players[i]["role"]
    
    game.phase = "role_reveal"
    game.status = "active"
    game.current_player_index = 0
    db.session.commit()

    socketio.emit(
        "game_started",
        {"room_code": room_code, "phase": "role_reveal"},
        room=room_code,
    )
    
    return redirect(url_for("lobby.multiplayer_role_reveal", room_code=room_code, player_token=player_token))


@lobby_bp.route("/multiplayer-role-reveal/<room_code>/<player_token>")
def multiplayer_role_reveal(room_code, player_token):
    """Display the multiplayer role reveal screen."""
    game = get_room(room_code)
    
    if not game:
        return redirect(url_for("lobby.index"))
    
    current_player = Player.query.filter_by(
        game_id=game.game_id,
        player_token=player_token
    ).first()
    
    if not current_player:
        return redirect(url_for("lobby.index"))
    
    players = Player.query.filter_by(game_id=game.game_id).all()

    if game.phase == "room_lobby" and len(players) >= game.num_players:
        player_data = [
            {"name": p.name, "color": p.color, "role": "crewmate", "is_bot": p.is_bot}
            for p in players
        ]
        assigned_players = assign_roles(player_data, game.imposter_count, game.jester_count)

        for i, player in enumerate(players):
            player.role = assigned_players[i]["role"]

        game.phase = "role_reveal"
        game.status = "active"
        game.current_player_index = 0
        db.session.commit()

        socketio.emit(
            "game_started",
            {"room_code": room_code, "phase": "role_reveal"},
            room=room_code,
        )

    # Find the current player's index
    player_index = 0
    for i, player in enumerate(players):
        if player.player_id == current_player.player_id:
            player_index = i
            break
    
    return render_template(
        "index.html",
        phase="multiplayer_role_reveal",
        game=game,
        room_code=room_code,
        players=players,
        current_player=current_player,
        current_player_index=player_index,
        word_categories=get_word_categories(),
    )


@lobby_bp.route("/mark-ready", methods=["POST"])
def mark_ready():
    """Mark the current player as ready."""
    room_code = request.form.get("room_code", "").strip().upper()
    player_token = request.form.get("player_token", "").strip()
    
    if not room_exists(room_code) or not player_token:
        return {"success": False}
    
    game = get_room(room_code)
    player = Player.query.filter_by(game_id=game.game_id, player_token=player_token).first()
    
    if player:
        player.is_ready = True
        db.session.commit()
        
        # Check if all players are ready
        all_players = Player.query.filter_by(game_id=game.game_id).all()
        all_ready = all(p.is_ready for p in all_players)
        
        if all_ready:
            game.phase = "game"
            db.session.commit()
            return {"success": True, "all_ready": True}
        
        return {"success": True, "all_ready": False}
    
    return {"success": False}


@lobby_bp.route("/submit-clue", methods=["POST"])
def submit_clue():
    """Submit a clue for the current round."""
    room_code = request.form.get("room_code", "").strip().upper()
    clue = request.form.get("clue", "").strip()
    player_token = request.form.get("player_token", "").strip()
    
    if not room_exists(room_code) or not clue or not player_token:
        return {"success": False}
    
    game = get_room(room_code)
    player = Player.query.filter_by(game_id=game.game_id, player_token=player_token).first()
    
    if player and not player.was_voted_out:
        from models import Round
        round_record = Round(
            game_id=game.game_id,
            round_number=game.round_number,
            clue_given=clue,
            player_id=player.player_id
        )
        db.session.add(round_record)
        db.session.commit()
        return {"success": True, "clue": clue, "player": player.name}
    
    return {"success": False}


@lobby_bp.route("/submit-vote", methods=["POST"])
def submit_vote():
    """Submit a vote to eliminate a player."""
    room_code = request.form.get("room_code", "").strip().upper()
    target_name = request.form.get("target", "").strip()
    player_token = request.form.get("player_token", "").strip()
    
    if not room_exists(room_code) or not target_name or not player_token:
        return {"success": False}
    
    game = get_room(room_code)
    voter = Player.query.filter_by(game_id=game.game_id, player_token=player_token).first()
    target = Player.query.filter_by(game_id=game.game_id, name=target_name).first()
    
    if voter and target and not voter.was_voted_out and not target.was_voted_out:
        from models import Vote
        vote = Vote(
            game_id=game.game_id,
            voter_id=voter.player_id,
            target_id=target.player_id
        )
        db.session.add(vote)
        db.session.commit()
        return {"success": True, "voter": voter.name, "target": target_name}
    
    return {"success": False}
