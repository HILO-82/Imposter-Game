"""
Logistic Regression voting bot.

Uses features: votes_received, round_number, players_remaining,
bot_role, clue_similarity_score to predict elimination likelihood per player.
"""

from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

from ml.generate_vote_data import generate_synthetic_vote_data

MODEL_PATH = Path(__file__).resolve().parent.parent / "lr_model.pkl"


def train_and_save():
    X, y = generate_synthetic_vote_data()
    # Logistic regression: P(eliminated) = sigmoid(w·x + b)
    model = LogisticRegression(max_iter=1000, random_state=42)
    model.fit(X, y)
    joblib.dump(model, MODEL_PATH)
    return model


def _load_model():
    if not MODEL_PATH.exists():
        train_and_save()
    return joblib.load(MODEL_PATH)


def _clue_similarity(player, clues, secret_word):
    """Heuristic: how well player's clue aligns with secret word metadata."""
    if not clues:
        return 0.5
    secret = secret_word.lower()
    best = 0.0
    for clue in clues:
        if not clue:
            continue
        tokens = clue.lower().split()
        for t in tokens:
            if t in secret or secret in t:
                best = max(best, 0.9)
            elif t[0] == secret[0] if secret else False:
                best = max(best, 0.5)
            else:
                best = max(best, 0.2)
    if player.role == "imposter":
        return 1.0 - best
    return best


def bot_vote(game_state):
    """
    game_state dict keys:
      players: list of {player_id, role, was_voted_out, is_bot}
      round_number, vote_counts: {player_id: count}, clues: {player_id: clue}
      secret_word, bot_role
    Returns player_id to vote for.
    """
    model = _load_model()
    alive = [p for p in game_state["players"] if not p["was_voted_out"] and not p["is_bot"]]
    if not alive:
        return None

    n_remaining = len([p for p in game_state["players"] if not p["was_voted_out"]])
    round_norm = min(game_state.get("round_number", 1), 7) / 7.0
    bot_role = 1 if game_state.get("bot_role") == "imposter" else 0
    vote_counts = game_state.get("vote_counts", {})
    clues = game_state.get("clues", {})
    secret = game_state.get("secret_word", "")

    best_id = None
    best_score = -1.0

    for p in alive:
        pid = p["player_id"]
        votes_received = vote_counts.get(pid, 0) / max(n_remaining, 1)
        sim = _clue_similarity(p, [clues.get(pid, "")], secret)
        features = np.array(
            [[votes_received, round_norm, n_remaining / 10.0, bot_role, sim]]
        )
        prob = model.predict_proba(features)[0][1]
        if prob > best_score:
            best_score = prob
            best_id = pid

    return best_id
