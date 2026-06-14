"""Input validation, rate limiting, and session checks (OWASP-aligned)."""

import re
import time
from collections import defaultdict
from functools import wraps

from flask import abort, session

from config import Config

NAME_PATTERN = re.compile(r"^[\w\s\-'.]{1,50}$", re.UNICODE)
HTML_TAG_PATTERN = re.compile(r"<[^>]*>")

# Sliding window rate limiter: {sid: [timestamps]}
# Each SocketIO session gets up to _RATE_LIMIT_MAX events per second.
# After a window of _RATE_LIMIT_WINDOW seconds, old timestamps expire.
# This prevents DoS attacks and runaway bot loops without permanently
# blocking legitimate users — the window slides so brief spikes pass.
_rate_limit_buckets: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_WINDOW = 1.0
_RATE_LIMIT_MAX = 10


def rate_limit(sid: str) -> bool:
    """Returns True if request is allowed, False if rate-limited."""
    now = time.time()
    bucket = _rate_limit_buckets[sid]
    # Prune timestamps outside the current window
    bucket[:] = [t for t in bucket if now - t < _RATE_LIMIT_WINDOW]
    if len(bucket) >= _RATE_LIMIT_MAX:
        return False
    bucket.append(now)
    return True


def strip_html(text: str) -> str:
    # Removes any HTML tags to prevent XSS attacks.
    # The regex <[^>]*> catches all tags like <script>, <img onerror>, etc.
    # Applied to user-supplied notes fields before storage and display.
    return HTML_TAG_PATTERN.sub("", text)


def validate_player_name(name):
    """Reject empty, oversized, or suspicious player names."""
    if not name or len(name) > Config.MAX_NAME_LENGTH:
        return False
    return bool(NAME_PATTERN.match(name.strip()))


def validate_clue(clue):
    if not clue or len(clue) > Config.MAX_CLUE_LENGTH:
        return False
    lowered = clue.lower()
    # Block common injection patterns: XSS (<script), SQL DML (drop table,
    # union select), and comment tokens (--, /*) used to bypass filters.
    # These are checked case-insensitively since SQL/JS keywords are
    # case-insensitive.
    blocked = ("<script", "drop table", "union select", "--", "/*")
    return not any(b in lowered for b in blocked)


def validate_message(message):
    """Validate chat message: non-empty, max length, no HTML."""
    if not message or len(message) > 500:
        return False
    # Reject messages containing any HTML tags — this catches
    # <script>, <img>, <a>, <iframe>, and any other tag that
    # could be used for XSS, CSRF token theft, or defacement.
    if HTML_TAG_PATTERN.search(message):
        return False
    return True


def validate_positive_int(value, min_val=1, max_val=20):
    try:
        n = int(value)
        return min_val <= n <= max_val
    except (TypeError, ValueError):
        return False


def require_game_session(game_id):
    if session.get("game_id") != game_id:
        abort(403)


def game_session_required(f):
    @wraps(f)
    def decorated(game_id, *args, **kwargs):
        require_game_session(game_id)
        return f(game_id, *args, **kwargs)
    return decorated
