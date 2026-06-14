import random

import numpy as np
from sklearn.naive_bayes import GaussianNB

from extensions import db
from models import Game, GameEvent, Player


def _encoded_label(winning_role):
    # Convert string role to integer for GaussianNB (which requires numeric y)
    mapping = {"crewmate": 0, "imposter": 1, "jester": 2}
    return mapping.get(winning_role, 0)


def _decoded_label(label):
    # Convert numeric prediction back to display string
    mapping = {0: "Crewmates", 1: "Imposters", 2: "Jester"}
    return mapping.get(label, "Crewmates")


def compute_insights():
    games = Game.query.filter(Game.status == "finished", Game.winning_role.isnot(None)).all()
    insights = {
        "total_games": len(games),
        "win_counts": {"crewmate": 0, "imposter": 0, "jester": 0},
        "by_player_count": {},
        "by_category": {},
        "avg_imposter_round": None,
    }
    imposter_rounds = []
    for g in games:
        role = g.winning_role
        insights["win_counts"][role] = insights["win_counts"].get(role, 0) + 1
        pc = str(g.num_players)
        if pc not in insights["by_player_count"]:
            insights["by_player_count"][pc] = {"crewmate": 0, "imposter": 0, "jester": 0}
        insights["by_player_count"][pc][role] = insights["by_player_count"][pc].get(role, 0) + 1
        cat = g.category or "Unknown"
        if cat not in insights["by_category"]:
            insights["by_category"][cat] = {"crewmate": 0, "imposter": 0, "jester": 0}
        insights["by_category"][cat][role] = insights["by_category"][cat].get(role, 0) + 1

        events = GameEvent.query.filter_by(game_id=g.game_id).all()
        for e in events:
            if e.event_type == "imposter_out":
                imposter_rounds.append(e.round_number)

    if imposter_rounds:
        insights["avg_imposter_round"] = round(sum(imposter_rounds) / len(imposter_rounds), 1)

    return insights


def build_model():
    # Gaussian Naive Bayes classifier trained on finished games.
    # Features: [player_count, imposter_count, jester_count, category_id]
    # These numeric game-config features are assumed independent and normally
    # distributed per class — a reasonable fit because game setup values are
    # chosen from fixed ranges and categories are encoded consistently.
    # Requires at least 3 finished games to produce a minimally useful model.
    games = Game.query.filter(Game.status == "finished", Game.winning_role.isnot(None)).all()
    if len(games) < 3:
        return None
    X, y = [], []
    category_map = {}
    cat_idx = 0
    for g in games:
        if g.category not in category_map:
            category_map[g.category] = cat_idx
            cat_idx += 1
        X.append([g.num_players, g.imposter_count, g.jester_count, category_map[g.category]])
        y.append(_encoded_label(g.winning_role))
    model = GaussianNB()
    model.fit(np.array(X), np.array(y))
    return model, category_map


def predict_winner(num_players, imposter_count, jester_count, category):
    # Rebuilds the model on every call so new finished games feed back
    # immediately without manual retraining. predict_proba returns per-class
    # probabilities; we take the highest as confidence.
    bundle = build_model()
    if bundle is None:
        return None
    model, category_map = bundle
    cat_enc = category_map.get(category, 0)
    X_pred = np.array([[num_players, imposter_count, jester_count, cat_enc]])
    pred = model.predict(X_pred)[0]
    proba = model.predict_proba(X_pred)[0]
    return _decoded_label(pred), round(float(max(proba)) * 100, 1)


def random_tip():
    insights = compute_insights()
    tips = []

    if insights["total_games"] == 0:
        return None

    wc = insights["win_counts"]
    total = insights["total_games"]
    crew_pct = round(wc.get("crewmate", 0) / total * 100)
    imp_pct = round(wc.get("imposter", 0) / total * 100)
    jest_pct = round(wc.get("jester", 0) / total * 100)

    tips.append(f"Overall: Crewmates win {crew_pct}%, Imposters {imp_pct}%, Jester {jest_pct}% (based on {total} games)")

    for pc, counts in sorted(insights["by_player_count"].items()):
        c = sum(counts.values())
        if c > 0:
            tips.append(f"In {pc}-player games: Crewmates win {round(counts.get('crewmate', 0) / c * 100)}%")

    for cat, counts in sorted(insights["by_category"].items()):
        c = sum(counts.values())
        if c >= 2:
            tips.append(f"Category '{cat}': Crewmates win {round(counts.get('crewmate', 0) / c * 100)}%")

    if insights["avg_imposter_round"] is not None:
        tips.append(f"Imposters are typically caught around round {insights['avg_imposter_round']}")

    return random.choice(tips)


GAME_NAMES = [
    ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"],
    ["Grace", "Hank", "Iris", "Jack", "Kate", "Leo"],
    ["Mia", "Noah", "Olivia", "Pete", "Quinn", "Rosa"],
    ["Sam", "Tina", "Uma", "Vince", "Wendy", "Xander"],
    ["Yara", "Zack", "Amy", "Ben", "Cara", "Dave"],
    ["Elsa", "Finn", "Gwen", "Hugo", "Ivy", "Jake"],
    ["Kara", "Liam", "Mona", "Nate", "Opal", "Pablo"],
    ["Rita", "Sean", "Tara", "Umar", "Vera", "Will"],
]

FAKE_WORDS = ["Galaxy", "Piano", "Sunset", "Cactus", "Rocket", "Puzzle", "Lantern", "Tornado"]


def seed_example_games():
    finished = Game.query.filter(Game.status == "finished").count()
    if finished > 0:
        return

    for i, names in enumerate(GAME_NAMES):
        word = FAKE_WORDS[i]
        imposter_count = 1 if i % 2 == 0 else 2
        jester_count = 1 if i < 4 else 0
        role = random.choice(["crewmate", "imposter", "jester"])
        base_rounds = random.randint(3, 6)

        game = Game(
            room_code=f"SEED{i:03d}",
            num_players=len(names),
            imposter_count=imposter_count,
            jester_count=jester_count,
            jester_info="nothing",
            secret_word=word,
            category=random.choice(["Animals", "Food", "Sports", "Music"]),
            status="finished",
            phase="vote",
            round_number=base_rounds,
            is_multi_device=False,
            winning_role=role,
        )
        db.session.add(game)
        db.session.flush()

        for j, n in enumerate(names):
            p_role = "crewmate"
            # assign some imposters/jesters based on game config
            if j < imposter_count:
                p_role = "imposter"
            elif j < imposter_count + jester_count:
                p_role = "jester"
            player = Player(
                game_id=game.game_id,
                name=n,
                role=p_role,
                was_voted_out=False,
                player_token=None,
                color=["#7c3aed", "#10b981", "#f59e0b", "#ef4444", "#3b82f6", "#ec4899", "#14b8a6", "#f97316"][j % 8],
            )
            db.session.add(player)
            db.session.flush()

            # record some events
            if j < imposter_count and role == "crewmate":
                out_round = random.randint(2, base_rounds)
                db.session.add(GameEvent(
                    game_id=game.game_id,
                    round_number=out_round,
                    player_id=player.player_id,
                    event_type="imposter_out",
                ))
            elif j == imposter_count and role == "jester":
                out_round = random.randint(1, base_rounds)
                db.session.add(GameEvent(
                    game_id=game.game_id,
                    round_number=out_round,
                    player_id=player.player_id,
                    event_type="jester_out",
                ))

    db.session.commit()


CATEGORY_LABELS = {
    "Animals": "Balanced starter category",
    "Food": "Tends to favor Crewmates",
    "Sports": "Tends to favor Imposters",
    "Music": "Balanced",
    "Nature": "Slightly Crewmate-favored",
    "Technology": "Imposter-favored",
    "Travel": "Balanced",
    "Science": "Crewmate-favored",
}


def get_category_difficulty():
    """Return per-category win rates with a difficulty label."""
    games = Game.query.filter(Game.status == "finished", Game.winning_role.isnot(None)).all()
    cats = {}
    for g in games:
        cat = g.category or "Unknown"
        if cat not in cats:
            cats[cat] = {"crewmate": 0, "imposter": 0, "jester": 0, "total": 0}
        cats[cat][g.winning_role] += 1
        cats[cat]["total"] += 1

    result = []
    for cat, counts in sorted(cats.items()):
        c = counts["total"]
        crew_pct = round(counts["crewmate"] / c * 100)
        imp_pct = round(counts["imposter"] / c * 100)
        jest_pct = round(counts["jester"] / c * 100)
        label = CATEGORY_LABELS.get(cat, "No data")

        if c >= 2:
            diff = abs(crew_pct - imp_pct)
            if diff <= 15:
                label = "Well-balanced"
            elif crew_pct > imp_pct + 15:
                label = "Crewmate-favored"
            else:
                label = "Imposter-favored"

        result.append({
            "name": cat,
            "total": c,
            "crewmate_pct": crew_pct,
            "imposter_pct": imp_pct,
            "jester_pct": jest_pct,
            "label": label,
        })
    return result


def balanced_category_pick():
    """Pick a category weighted toward balanced ones or those needing more data."""
    # Categories with no data get weight 3 (high) to collect samples quickly.
    # Categories with balanced outcomes (crewmate_pct ≈ imposter_pct) score
    # higher — the balance metric is 100 - |crewmate_pct - imposter_pct|,
    # divided by 10 so weights stay in a reasonable range. Uses the same
    # proportional selection (roulette wheel) as the role assignment.
    diffs = get_category_difficulty()
    if not diffs:
        return None
    weights = []
    for d in diffs:
        if d["total"] == 0:
            w = 3
        else:
            balance = 100 - abs(d["crewmate_pct"] - d["imposter_pct"])
            w = max(1, balance / 10)
        weights.append(w)
    total_w = sum(weights)
    r = random.uniform(0, total_w)
    cumulative = 0
    for i, d in enumerate(diffs):
        cumulative += weights[i]
        if r <= cumulative:
            return d["name"]
    return diffs[-1]["name"]


def get_word_ratings():
    games = Game.query.filter(Game.status == "finished", Game.winning_role.isnot(None)).all()
    words = {}
    for g in games:
        w = g.secret_word
        if w not in words:
            words[w] = {"imposter_wins": 0, "crewmate_wins": 0, "jester_wins": 0, "total": 0, "category": g.category}
        words[w][g.winning_role + "_wins"] += 1
        words[w]["total"] += 1
    result = []
    for word, data in sorted(words.items()):
        t = data["total"]
        crew_pct = round(data["crewmate_wins"] / t * 100) if t else 0
        imp_pct = round(data["imposter_wins"] / t * 100) if t else 0
        balance = 100 - abs(crew_pct - imp_pct)
        result.append({**data, "word": word, "crewmate_pct": crew_pct, "imposter_pct": imp_pct, "balance": balance})
    return result


def balanced_word(category=None):
    ratings = get_word_ratings()
    pool = [r for r in ratings if (category is None or r["category"] == category) and r["total"] >= 1]
    if not pool:
        return None
    weights = [max(1, r["balance"] / 10) for r in pool]
    total_w = sum(weights)
    r = random.uniform(0, total_w)
    cumulative = 0
    for i, w in enumerate(pool):
        cumulative += weights[i]
        if r <= cumulative:
            return w["word"]
    return pool[-1]["word"]
