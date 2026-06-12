from extensions import db
from models import Word
import random


def get_all_words():
    return Word.query.all()


def get_word_categories():
    categories = db.session.query(Word.category).distinct().all()
    return sorted([c[0] for c in categories])


def lookup_word(word):
    return Word.query.filter_by(word=word.strip().lower()).first()


def random_word(category=None):
    query = Word.query
    if category:
        query = query.filter_by(category=category)
    pool = query.all()
    return random.choice(pool) if pool else None


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
