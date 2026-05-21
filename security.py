"""Input validation and session checks (OWASP-aligned)."""

import re
from functools import wraps

from flask import abort, session

from config import Config

NAME_PATTERN = re.compile(r"^[\w\s\-'.]{1,50}$", re.UNICODE)


def validate_player_name(name):
    """Reject empty, oversized, or suspicious player names."""
    if not name or len(name) > Config.MAX_NAME_LENGTH:
        return False
    return bool(NAME_PATTERN.match(name.strip()))


def validate_clue(clue):
    if not clue or len(clue) > Config.MAX_CLUE_LENGTH:
        return False
    # Block obvious SQL/script injection patterns in free text
    lowered = clue.lower()
    blocked = ("<script", "drop table", "union select", "--", "/*")
    return not any(b in lowered for b in blocked)


def validate_positive_int(value, min_val=1, max_val=20):
    try:
        n = int(value)
        return min_val <= n <= max_val
    except (TypeError, ValueError):
        return False


def require_game_session(game_id):
    """Ensure session game_id matches URL — prevents cross-game access."""
    if session.get("game_id") != game_id:
        abort(403)


def game_session_required(f):
    @wraps(f)
    def decorated(game_id, *args, **kwargs):
        require_game_session(game_id)
        return f(game_id, *args, **kwargs)

    return decorated
