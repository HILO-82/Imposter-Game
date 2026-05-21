"""
KNN word-guessing bot.

Trains on word feature vectors [category_id, subcategory_id, word_length, commonality].
At inference, clue text is mapped to an estimated feature vector (length + avg stats),
then KNN finds the nearest dictionary word.
"""

from pathlib import Path

import joblib
import numpy as np
from sklearn.neighbors import KNeighborsClassifier

from words import get_all_words, lookup_word

MODEL_PATH = Path(__file__).resolve().parent.parent / "knn_model.pkl"
KNN_NEIGHBORS = 5


def _feature_matrix():
    words = get_all_words()
    X = np.array(
        [
            [w["category_id"], w["subcategory_id"], w["word_length"], w["commonality"]]
            for w in words
        ]
    )
    y = np.array([w["word"] for w in words])
    return X, y, words


def train_and_save():
    """Fit KNN on all dictionary words and persist model."""
    X, y, _ = _feature_matrix()
    # k-NN: classify word label from feature space (majority vote of k neighbors)
    model = KNeighborsClassifier(n_neighbors=KNN_NEIGHBORS, weights="distance")
    model.fit(X, y)
    joblib.dump({"model": model, "words": get_all_words()}, MODEL_PATH)
    return model


def _load_model():
    if not MODEL_PATH.exists():
        train_and_save()
    return joblib.load(MODEL_PATH)


def clues_to_features(clues):
    """
    Map clue strings to a single feature vector.
    Uses average word_length and commonality from known clue tokens;
    category/subcategory default to median if unknown.
    """
    words = get_all_words()
    if not clues:
        mid = words[len(words) // 2]
        return np.array(
            [[mid["category_id"], mid["subcategory_id"], mid["word_length"], mid["commonality"]]]
        )

    matched = []
    lengths = []
    for clue in clues:
        for token in clue.lower().split():
            meta = lookup_word(token)
            if meta:
                matched.append(meta)
            lengths.append(len(token))

    if matched:
        cat = int(np.mean([m["category_id"] for m in matched]))
        sub = int(np.mean([m["subcategory_id"] for m in matched]))
        wl = int(np.mean([m["word_length"] for m in matched]))
        com = float(np.mean([m["commonality"] for m in matched]))
    else:
        wl = int(np.mean(lengths)) if lengths else 5
        cat, sub, com = 5, 1, 0.5

    return np.array([[cat, sub, wl, com]])


def bot_guess(clues, secret_category=None):
    """
    Return best-guess word from clues using trained KNN.
    Falls back to most common word in category if prediction unknown.
    """
    bundle = _load_model()
    model = bundle["model"]
    X = clues_to_features(clues)
    pred = model.predict(X)[0]

    if lookup_word(pred):
        return pred

    # Category-level fallback for custom/unknown words
    words = get_all_words()
    if secret_category:
        pool = [w for w in words if w["category"] == secret_category]
    else:
        pool = words
    if pool:
        pool.sort(key=lambda w: w["commonality"], reverse=True)
        return pool[0]["word"]
    return words[0]["word"] if words else "unknown"
