"""Generate synthetic training data for logistic regression vote bot."""

import numpy as np

FEATURE_COUNT = 5
SAMPLES = 2000


def generate_synthetic_vote_data(n_samples=SAMPLES, random_state=42):
    """
    Features:
    0 votes_received (normalized 0-1)
    1 round_number (normalized)
    2 players_remaining (normalized)
    3 bot_role (0=crewmate bot, 1=imposter bot)
    4 clue_similarity_score (0-1)
    Label: 1 if player was voted out this round, else 0
    """
    rng = np.random.default_rng(random_state)
    X = []
    y = []
    for _ in range(n_samples):
        votes_received = rng.uniform(0, 1)
        round_number = rng.integers(1, 8) / 7.0
        players_remaining = rng.integers(3, 10) / 9.0
        bot_role = rng.integers(0, 2)
        clue_similarity = rng.uniform(0, 1)

        # Higher votes + suspicious clues => more likely eliminated
        imposter_suspicion = (1 - clue_similarity) * 0.4 + votes_received * 0.5
        if bot_role == 1:
            imposter_suspicion *= 0.7
        eliminated = 1 if imposter_suspicion + rng.normal(0, 0.15) > 0.55 else 0

        X.append(
            [votes_received, round_number, players_remaining, bot_role, clue_similarity]
        )
        y.append(eliminated)

    return np.array(X), np.array(y)
