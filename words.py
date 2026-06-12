import json
import random
from pathlib import Path

from extensions import db
from models import Word

WORDS_PATH = Path(__file__).resolve().parent / "data" / "words.json"

_words_cache = None


def _get_words():
    global _words_cache
    if _words_cache is None:
        with open(WORDS_PATH, encoding="utf-8") as f:
            _words_cache = json.load(f)
    return _words_cache


def get_all_words():
    return _get_words()


def get_word_categories():
    words = _get_words()
    return sorted({w["category"] for w in words})


def lookup_word(word):
    target = word.strip().lower()
    for w in _get_words():
        if w["word"] == target:
            return w
    return None


def random_word(category=None):
    words = _get_words()
    pool = [w for w in words if w["category"] == category] if category else words
    return random.choice(pool) if pool else None


def seed_words_table(db_session, Word):
    if Word.query.count() > 0:
        return
    for entry in _get_words():
        row = Word(
            word=entry["word"],
            category_id=entry["category_id"],
            subcategory_id=entry["subcategory_id"],
            word_length=entry["word_length"],
            commonality=entry["commonality"],
        )
        db_session.add(row)
    db_session.commit()
