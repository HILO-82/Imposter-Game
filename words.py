import json
from pathlib import Path

WORDS_PATH = Path(__file__).resolve().parent / "data" / "words.json"
_CATEGORY_TO_ID = {}
_WORD_LOOKUP = {}


def _load_words():
    global _WORD_LOOKUP, _CATEGORY_TO_ID  # noqa: PLW0603
    if _WORD_LOOKUP:
        return
    lookup = {}
    cat_map = {}
    with open(WORDS_PATH, encoding="utf-8") as f:
        entries = json.load(f)
    for entry in entries:
        lookup[entry["word"]] = entry
        cat_map[entry["category"]] = entry["category_id"]
    _WORD_LOOKUP = lookup
    _CATEGORY_TO_ID = cat_map


def get_all_words():
    _load_words()
    return list(_WORD_LOOKUP.values())


def get_word_categories():
    _load_words()
    return sorted(_CATEGORY_TO_ID.keys())


def lookup_word(word):
    _load_words()
    return _WORD_LOOKUP.get(word.strip().lower())


def random_word(category=None):
    _load_words()
    import random

    if category and category in _CATEGORY_TO_ID:
        pool = [w for w in _WORD_LOOKUP.values() if w["category"] == category]
    else:
        pool = list(_WORD_LOOKUP.values())
    return random.choice(pool) if pool else None  # nosec B311 — game word pick


def seed_words_table(db_session, Word):
    """Insert dictionary words into DB if empty."""
    if Word.query.count() > 0:
        return
    for entry in get_all_words():
        row = Word(
            word=entry["word"],
            category_id=entry["category_id"],
            subcategory_id=entry["subcategory_id"],
            word_length=entry["word_length"],
            commonality=entry["commonality"],
        )
        db_session.add(row)
    db_session.commit()
