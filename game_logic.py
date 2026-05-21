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
    }


def assign_roles(players_data, imposter_count, jester_count):
    """Shuffle and assign imposter/jester/crewmate roles."""
    n = len(players_data)
    indices = list(range(n))
    random.shuffle(indices)
    roles = ["crewmate"] * n
    idx = 0
    for _ in range(min(imposter_count, n)):
        roles[indices[idx]] = "imposter"
        idx += 1
    if jester_count > 0 and idx < n:
        roles[indices[idx]] = "jester"
    for i, p in enumerate(players_data):
        p["role"] = roles[i]
    return players_data


def create_game_from_setup(setup, include_bot=True):
    """Persist game + players; returns Game."""
    secret = setup.get("secret_word", "").strip().lower()
    category = setup.get("word_category", "Animals")
    word_meta = lookup_word(secret) if secret else None
    if not word_meta:
        word_meta = random_word(category if category != "custom" else None)
        secret = word_meta["word"]
        category = word_meta["category"]

    human_count = len(setup["players"])
    game = Game(
        num_players=human_count + (1 if include_bot else 0),
        secret_word=secret,
        category=category,
        status="active",
        round_number=1,
        phase="clue",
    )
    db.session.add(game)
    db.session.flush()

    for p in setup["players"]:
        player = Player(
            game_id=game.game_id,
            name=p["name"],
            role=p["role"],
            color=p.get("color", "#ff0000"),
            is_bot=False,
        )
        db.session.add(player)

    if include_bot:
        bot = Player(
            game_id=game.game_id,
            name="AI Bot",
            role="imposter",
            color="#333333",
            is_bot=True,
        )
        db.session.add(bot)

    db.session.commit()
    return game


def alive_players(game_id):
    return Player.query.filter_by(game_id=game_id, was_voted_out=False).all()


def clues_for_round(game_id, round_number):
    return Round.query.filter_by(game_id=game_id, round_number=round_number).all()


def all_clues_submitted(game):
    alive = [p for p in alive_players(game.game_id) if not p.is_bot]
    clues = clues_for_round(game.game_id, game.round_number)
    return len(clues) >= len(alive)


def tally_votes(game_id, round_number):
    round_ids = [
        r.round_id
        for r in Round.query.filter_by(game_id=game_id, round_number=round_number).all()
    ]
    if round_ids:
        votes = Vote.query.filter(
            Vote.game_id == game_id, Vote.round_id.in_(round_ids)
        ).all()
    else:
        votes = Vote.query.filter_by(game_id=game_id).all()
    return Counter(v.target_id for v in votes)


def eliminate_top_voted(game):
    """Eliminate player with most votes; return eliminated Player or None."""
    counts = tally_votes(game.game_id, game.round_number)
    if not counts:
        return None
    max_votes = max(counts.values())
    top = [pid for pid, c in counts.items() if c == max_votes]
    target_id = random.choice(top)  # nosec B311 — gameplay tie-break, not cryptography
    player = Player.query.get(target_id)
    if player:
        player.was_voted_out = True
        db.session.commit()
    return player


def check_win_condition(game):
    """
    Returns winning_role string or None if game continues.
    crewmate: all imposters out
    imposter: imposters >= crewmates alive
    jester: jester voted out
    """
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
