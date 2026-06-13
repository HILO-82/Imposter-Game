import random
from collections import defaultdict

from extensions import db
from models import Game, GameEvent, Player


def get_player_stats():
    games = Game.query.filter(Game.status == "finished", Game.winning_role.isnot(None)).all()
    stats = defaultdict(lambda: {
        "games_played": 0, "games_won": 0,
        "as_imposter": 0, "imposter_wins": 0,
        "as_crewmate": 0, "crewmate_wins": 0,
        "as_jester": 0, "jester_wins": 0,
        "imposter_rounds": [], "crewmate_rounds": [],
        "first_eliminations": 0,
        "starts": 0, "start_wins": 0, "start_losses": 0,
    })

    for g in games:
        players = Player.query.filter_by(game_id=g.game_id).all()
        events = GameEvent.query.filter_by(game_id=g.game_id).all()
        out_rounds = {e.player_id: e.round_number for e in events}
        first_out = {e.player_id for e in events if e.round_number == 1}

        for p in players:
            s = stats[p.name]
            s["games_played"] += 1
            won = g.winning_role == p.role

            if g.starter_player_name and p.name == g.starter_player_name:
                s["starts"] += 1
                if won:
                    s["start_wins"] += 1
                else:
                    s["start_losses"] += 1

            if p.role == "imposter":
                s["as_imposter"] += 1
                if won:
                    s["imposter_wins"] += 1
                if p.player_id in out_rounds:
                    s["imposter_rounds"].append(out_rounds[p.player_id])
                if p.player_id in first_out:
                    s["first_eliminations"] += 1
            elif p.role == "crewmate":
                s["as_crewmate"] += 1
                if won:
                    s["crewmate_wins"] += 1
                if p.player_id in out_rounds:
                    s["crewmate_rounds"].append(out_rounds[p.player_id])
            else:
                s["as_jester"] += 1
                if won:
                    s["jester_wins"] += 1

            if won:
                s["games_won"] += 1

    return dict(stats)


def imposter_score(name, stats):
    s = stats.get(name, {})
    gp = s.get("games_played", 0)
    if gp == 0:
        return 50.0
    cwr = s.get("crewmate_wins", 0) / max(s.get("as_crewmate", 0), 1)
    iwr = s.get("imposter_wins", 0) / max(s.get("as_imposter", 0), 1)
    imp_rounds = s.get("imposter_rounds", [])
    avg_imp_surv = sum(imp_rounds) / max(len(imp_rounds), 1) if imp_rounds else 0
    times_imp = s.get("as_imposter", 0)
    crew_rounds = s.get("crewmate_rounds", [])
    avg_crew_surv = sum(crew_rounds) / max(len(crew_rounds), 1) if crew_rounds else 0
    first_elim = s.get("first_eliminations", 0)
    # Higher = more likely to get imposter
    return (cwr * 50 - iwr * 30 + avg_crew_surv * 10
            - avg_imp_surv * 5 - times_imp * 2 + first_elim * 15)


def start_player_score(name, stats):
    s = stats.get(name, {})
    gp = s.get("games_played", 0)
    if gp == 0:
        return 50.0
    starts = s.get("starts", 0)
    start_wins = s.get("start_wins", 0)
    start_losses = s.get("start_losses", 0)
    return max(20, 100 - starts * 2 + start_losses * 3)


def _weighted_pick(candidates, score_fn, stats, count):
    if len(candidates) <= count:
        return candidates[:]
    scores = [max(score_fn(p, stats), 1) for p in candidates]
    picks = []
    pool = list(candidates)
    pool_scores = list(scores)
    for _ in range(count):
        total = sum(pool_scores)
        r = random.uniform(0, total)
        cumulative = 0
        for i, p in enumerate(pool):
            cumulative += pool_scores[i]
            if r <= cumulative:
                picks.append(p)
                pool.pop(i)
                pool_scores.pop(i)
                break
    return picks


def balanced_role_assign(players_data, imposter_count, jester_count):
    stats = get_player_stats()
    names = [p["name"] for p in players_data]

    imposters = _weighted_pick(names, imposter_score, stats, imposter_count)
    remaining = [n for n in names if n not in imposters]
    jesters = _weighted_pick(remaining, lambda n, s: 0.5, stats, jester_count)

    name_to_data = {p["name"]: p for p in players_data}
    for name in name_to_data:
        if name in imposters:
            name_to_data[name]["role"] = "imposter"
        elif name in jesters:
            name_to_data[name]["role"] = "jester"
        else:
            name_to_data[name]["role"] = "crewmate"

    return players_data


def pick_starting_player(players_data):
    stats = get_player_stats()
    names = [p["name"] for p in players_data]
    return _weighted_pick(names, start_player_score, stats, 1)[0]
