from flask import Blueprint, redirect, render_template, request, session, url_for

from game_logic import assign_roles, default_setup_state
from security import validate_player_name
from words import get_word_categories, random_word

lobby_bp = Blueprint("lobby", __name__)


def get_setup():
    if "setup" not in session:
        session["setup"] = default_setup_state()
    return session["setup"]


def save_setup(setup):
    session["setup"] = setup
    session.modified = True


@lobby_bp.route("/")
def index():
    setup = get_setup()
    setup["phase"] = "welcome"
    save_setup(setup)
    return render_template(
        "index.html",
        phase="welcome",
        game_state=setup,
        word_categories=get_word_categories(),
    )


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
    count = setup["player_count"]
    players = []
    for i in range(1, count + 1):
        name = request.form.get(f"player{i}", f"Player {i}").strip()
        if not validate_player_name(name):
            name = f"Player {i}"
        color = request.form.get(f"color{i}", "#ff0000")
        players.append({"name": name, "color": color, "role": "crewmate"})
    players = assign_roles(players, setup["imposter_count"], setup["jester_count"])
    setup["players"] = players
    setup["current_player_index"] = 0
    setup["phase"] = "role_reveal"
    save_setup(setup)
    return render_template(
        "index.html",
        phase="role_reveal",
        game_state=setup,
        word_categories=get_word_categories(),
    )


@lobby_bp.route("/reveal-role")
def reveal_role():
    setup = get_setup()
    setup["phase"] = "role_reveal"
    save_setup(setup)
    return render_template(
        "index.html",
        phase="role_reveal",
        game_state=setup,
        word_categories=get_word_categories(),
    )


@lobby_bp.route("/next-player")
def next_player():
    setup = get_setup()
    setup["current_player_index"] = setup.get("current_player_index", 0) + 1
    save_setup(setup)
    return render_template(
        "index.html",
        phase="role_reveal",
        game_state=setup,
        word_categories=get_word_categories(),
    )


@lobby_bp.route("/play-again")
def play_again():
    setup = get_setup()
    w = random_word(setup.get("word_category"))
    if w:
        setup["secret_word"] = w["word"]
        setup["word_category"] = w["category"]
    if setup.get("players"):
        names_colors = [(p["name"], p.get("color", "#ff0000")) for p in setup["players"]]
        players = [{"name": n, "color": c, "role": "crewmate"} for n, c in names_colors]
        setup["players"] = assign_roles(
            players, setup["imposter_count"], setup["jester_count"]
        )
    setup["current_player_index"] = 0
    setup["phase"] = "role_reveal"
    save_setup(setup)
    return render_template(
        "index.html",
        phase="role_reveal",
        game_state=setup,
        word_categories=get_word_categories(),
    )
