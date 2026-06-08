import random
import string
from extensions import db
from models import Game


def generate_room_code():
    """Generate a unique 6-character room code."""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        existing = Game.query.filter_by(room_code=code).first()
        if not existing:
            return code


def create_room(player_count, imposter_count, jester_count, jester_info, secret_word, category):
    """Create a new game room with the given settings."""
    room_code = generate_room_code()
    game = Game(
        room_code=room_code,
        num_players=player_count,
        imposter_count=imposter_count,
        jester_count=jester_count,
        jester_info=jester_info,
        secret_word=secret_word,
        category=category,
        status="lobby",
        phase="lobby"
    )
    db.session.add(game)
    db.session.commit()
    return game


def get_room(room_code):
    """Get a game room by its code."""
    return Game.query.filter_by(room_code=room_code).first()


def room_exists(room_code):
    """Check if a room with the given code exists."""
    return Game.query.filter_by(room_code=room_code).first() is not None
