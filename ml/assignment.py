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
    })

    for g in games:
        players = Player.query.filter_by(game_id=g.game_id).all()
        events = GameEvent.query.filter_by(game_id=g.game_id).all()
        out_rounds = {e.player_id: e.round_number for e in events}

        for p in players:
            s = stats[p.name]
            s["games_played"] += 1
            won = g.winning_role == p.role

            if p.role == "imposter":
                s["as_imposter"] += 1
                if won:
                    s["imposter_wins"] += 1
                if p.player_id in out_rounds:
                    s["imposter_rounds"].append(out_rounds[p.player_id])
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


def balanced_role_assign(players_data, imposter_count, jester_count):
    n = len(players_data)
    stats = get_player_stats()

    def score(name):
        s = stats.get(name, {})
        gp = s.get("games_played", 0)
        if gp == 0:
            return 0.5
        cwr = s.get("crewmate_wins", 0) / max(s.get("as_crewmate", 0), 1)
        iwr = s.get("imposter_wins", 0) / max(s.get("as_imposter", 0), 1)
        imp_rounds = s.get("imposter_rounds", [])
        avg_imp_surv = sum(imp_rounds) / max(len(imp_rounds), 1)
        times_imp = s.get("as_imposter", 0)
        crew_rounds = s.get("crewmate_rounds", [])
        avg_crew_surv = sum(crew_rounds) / max(len(crew_rounds), 1)
        return (cwr * 0.5 - iwr * 0.3 + avg_crew_surv * 0.1
                - avg_imp_surv * 0.05 - times_imp * 0.02)

    name_to_data = {p["name"]: p for p in players_data}
    scored = sorted(
        [(score(p["name"]), p["name"]) for p in players_data],
        reverse=True,
    )
    sorted_names = [name for _, name in scored]

    assigned = 0
    for i in range(min(imposter_count, n)):
        name_to_data[sorted_names[i]]["role"] = "imposter"
        assigned += 1
    for i in range(min(jester_count, n - assigned)):
        name_to_data[sorted_names[assigned + i]]["role"] = "jester"

    return players_data
