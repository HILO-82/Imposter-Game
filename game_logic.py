import random
from collections import Counter

from extensions import db
from models import Game, Player, Round, Vote
from words import lookup_word, random_word


def default_setup_state():
    return {
        "player_count": 6,
        "imposter_count": 1,
        "jester_count": 0,
        "jester_info": "nothing",
        "secret_word": "",
        "word_category": "Animals",
        "players": [],
        "current_player_index": 0,
        "phase": "welcome",
        "has_ai_bot": False,
        "saved_player_inputs": {},
    }


def assign_roles(players_data, imposter_count, jester_count):
    n = len(players_data)
    indices = list(range(n))
    random.shuffle(indices)
    roles = ["crewmate"] * n
    idx = 0
    for _ in range(min(imposter_count, n)):
        roles[indices[idx]] = "imposter"
        idx += 1
    for _ in range(min(jester_count, n - idx)):
        roles[indices[idx]] = "jester"
        idx += 1
    for i, p in enumerate(players_data):
        p["role"] = roles[i]
    return players_data


def alive_players(game_id):
    return Player.query.filter_by(game_id=game_id, was_voted_out=False).all()


def clues_for_round(game_id, round_number):
    return Round.query.filter_by(game_id=game_id, round_number=round_number).all()


def all_clues_submitted(game):
    alive = [p for p in alive_players(game.game_id) if not p.is_bot]
    clues = clues_for_round(game.game_id, game.round_number)
    return len(clues) >= len(alive)


def tally_votes(game_id, round_number):
    votes = Vote.query.filter_by(game_id=game_id, round_number=round_number).all()
    return Counter(v.target_id for v in votes)


def eliminate_top_voted(game):
    counts = tally_votes(game.game_id, game.round_number)
    if not counts:
        return None
    max_votes = max(counts.values())
    top = [pid for pid, c in counts.items() if c == max_votes]
    target_id = random.choice(top)
    player = Player.query.get(target_id)
    if player:
        player.was_voted_out = True
        db.session.commit()
    return player


def check_win_condition(game):
    players = Player.query.filter_by(game_id=game.game_id).all()
    alive = [p for p in players if not p.was_voted_out]
    alive_imposters = [p for p in alive if p.role == "imposter"]
    alive_crew = [p for p in alive if p.role == "crewmate"]
    voted_jester = [p for p in players if p.role == "jester" and p.was_voted_out]

    if voted_jester:
        return "jester"
    if not alive_imposters:
        return "crewmate"
    if len(alive_imposters) >= len(alive_crew):
        return "imposter"
    return None


def create_game_from_setup(setup):
    """Create a local pass-and-play game from a setup dict."""
    from room_manager import generate_room_code

    players_data = setup["players"]
    imposter_count = setup.get("imposter_count", 1)
    jester_count = setup.get("jester_count", 0)
    jester_info = setup.get("jester_info", "nothing")
    secret_word = setup.get("secret_word") or random_word(setup.get("word_category"))["word"]
    category = setup.get("word_category", "Animals")

    game = Game(
        room_code=generate_room_code(),
        num_players=len(players_data),
        imposter_count=imposter_count,
        jester_count=jester_count,
        jester_info=jester_info,
        secret_word=secret_word,
        category=category,
        status="active",
        phase="clue",
        round_number=1,
        current_player_index=0,
    )
    db.session.add(game)
    db.session.flush()

    assign_roles(players_data, imposter_count, jester_count)
    for p in players_data:
        player = Player(
            game_id=game.game_id,
            name=p["name"],
            role=p["role"],
            color=p.get("color", "#ff0000"),
        )
        db.session.add(player)

    db.session.commit()
    return game
