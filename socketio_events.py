from flask import request, session
from flask_socketio import emit, join_room

from extensions import db
from models import Game, Player, Round, Vote
from game_logic import alive_players, all_clues_submitted, tally_votes, eliminate_top_voted, check_win_condition
from security import validate_clue, rate_limit


def _serialize_players(game_id):
    players = Player.query.filter_by(game_id=game_id).order_by(Player.player_id).all()
    return [
        {
            "player_id": p.player_id,
            "name": p.name,
            "color": p.color,
            "is_bot": p.is_bot,
            "was_voted_out": p.was_voted_out,
            "role": p.role,
        }
        for p in players
    ]


def _serialize_clues(game_id, round_number):
    clues = Round.query.filter_by(game_id=game_id, round_number=round_number).all()
    return [
        {
            "player_name": c.player.name,
            "player_color": c.player.color,
            "clue": c.clue_given,
            "player_id": c.player_id,
        }
        for c in clues
    ]


def register_socketio_events(socketio):

    @socketio.on("connect")
    def handle_connect():
        pass

    @socketio.on("disconnect")
    def handle_disconnect():
        room_code = session.get("room_code")
        if room_code:
            game = Game.query.filter_by(room_code=room_code).first()
            if game and game.is_multi_device:
                emit("players_updated", {"players": _serialize_players(game.game_id)}, room=room_code)

    @socketio.on("join_game")
    def handle_join_game(data):
        room_code = data.get("room_code")
        token = data.get("token")
        is_host = data.get("is_host", False)

        if not room_code:
            return
        game = Game.query.filter_by(room_code=room_code).first()
        if not game:
            return

        join_room(room_code)

        if is_host and game.is_multi_device:
            if token and token == game.host_token:
                join_room(f"host_{game.game_id}")
                emit("players_updated", {"players": _serialize_players(game.game_id)}, room=room_code)
                emit("game_state", {
                    "phase": game.phase,
                    "round": game.round_number,
                    "status": game.status,
                }, room=room_code)
            return

        if token:
            player = Player.query.filter_by(game_id=game.game_id, player_token=token).first()
            if player:
                join_room(token)
                player.is_connected = True
                db.session.commit()
                emit("players_updated", {"players": _serialize_players(game.game_id)}, room=room_code)

    @socketio.on("start_game")
    def handle_start_game(data):
        room_code = data.get("room_code")
        host_token = data.get("host_token")

        game = Game.query.filter_by(room_code=room_code, is_multi_device=True).first()
        if not game or game.host_token != host_token:
            return

        if game.phase != "lobby":
            return

        players = Player.query.filter_by(game_id=game.game_id).all()
        unassigned = [p for p in players if not p.player_token]
        if unassigned:
            emit("error", {"message": "Waiting for all players to join"}, room=f"host_{game.game_id}")
            return

        game.phase = "role_reveal"
        game.status = "roles"
        game.round_number = 1
        db.session.commit()

        emit("game_starting", {"room_code": room_code}, room=room_code)

        from words import random_word as rw
        for p in players:
            role_data = {
                "player_id": p.player_id,
                "role": p.role,
                "color": p.color,
                "is_bot": p.is_bot,
            }
            if p.role == "crewmate":
                role_data["secret_word"] = game.secret_word
                role_data["category"] = game.category
            elif p.role == "jester":
                if game.jester_info == "category":
                    role_data["jester_info"] = f"Category: {game.category}"
                elif game.jester_info == "partial":
                    role_data["jester_info"] = f"Partial word: {game.secret_word[:3]}..."
                elif game.jester_info == "full":
                    role_data["jester_info"] = f"Full word: {game.secret_word}"
                else:
                    role_data["jester_info"] = "No word information"

            if p.player_token:
                emit("your_role", role_data, room=p.player_token)

    @socketio.on("advance_phase")
    def handle_advance_phase(data):
        room_code = data.get("room_code")
        host_token = data.get("host_token")

        game = Game.query.filter_by(room_code=room_code, is_multi_device=True).first()
        if not game or game.host_token != host_token:
            return

        if game.phase == "role_reveal":
            game.phase = "clue"
            db.session.commit()
            emit("phase_changed", {"phase": "clue", "round": game.round_number}, room=room_code)

    @socketio.on("submit_clue")
    def handle_submit_clue(data):
        if not rate_limit(request.sid):
            return
        room_code = data.get("room_code")
        token = data.get("token")
        raw_clue = data.get("clue", "").strip()

        if not room_code or not token or not validate_clue(raw_clue):
            return

        game = Game.query.filter_by(room_code=room_code, is_multi_device=True).first()
        if not game or game.phase != "clue":
            return

        player = Player.query.filter_by(game_id=game.game_id, player_token=token).first()
        if not player or player.was_voted_out:
            return

        existing = Round.query.filter_by(
            game_id=game.game_id, round_number=game.round_number, player_id=player.player_id
        ).first()
        if existing:
            existing.clue_given = raw_clue
        else:
            db.session.add(Round(
                game_id=game.game_id,
                round_number=game.round_number,
                clue_given=raw_clue,
                player_id=player.player_id,
            ))
        db.session.commit()

        emit("clue_submitted", {
            "player_name": player.name,
            "clue": raw_clue,
            "player_id": player.player_id,
        }, room=room_code)

        if all_clues_submitted(game):
            game.phase = "vote"
            db.session.commit()
            emit("phase_changed", {"phase": "vote", "round": game.round_number}, room=room_code)

    @socketio.on("cast_vote")
    def handle_cast_vote(data):
        if not rate_limit(request.sid):
            return
        room_code = data.get("room_code")
        token = data.get("token")
        target_id = data.get("target_id")

        if not room_code or not token or not target_id:
            return

        game = Game.query.filter_by(room_code=room_code, is_multi_device=True).first()
        if not game or game.phase != "vote":
            return

        voter = Player.query.filter_by(game_id=game.game_id, player_token=token).first()
        target = Player.query.get(target_id)
        if not voter or not target or voter.was_voted_out or target.was_voted_out:
            return

        existing_vote = Vote.query.filter_by(
            game_id=game.game_id, round_number=game.round_number, voter_id=voter.player_id
        ).first()
        if existing_vote:
            return

        db.session.add(Vote(
            game_id=game.game_id,
            round_number=game.round_number,
            voter_id=voter.player_id,
            target_id=target.player_id,
        ))
        db.session.commit()

        emit("vote_cast", {"player_name": voter.name, "count": Vote.query.filter_by(game_id=game.game_id, round_number=game.round_number).count()}, room=room_code)

        alive_humans = [p for p in alive_players(game.game_id) if not p.is_bot]
        votes_this_round = Vote.query.filter_by(
            game_id=game.game_id, round_number=game.round_number
        ).all()
        voters_this_round = set(v.voter_id for v in votes_this_round)
        human_voter_ids = set(p.player_id for p in alive_humans)

        if human_voter_ids.issubset(voters_this_round):
            eliminated = eliminate_top_voted(game)
            winner = check_win_condition(game)

            tally = dict(tally_votes(game.game_id, game.round_number))
            emit("vote_results", {
                "tally": {str(k): v for k, v in tally.items()},
                "eliminated_player": eliminated.name if eliminated else None,
                "players": _serialize_players(game.game_id),
            }, room=room_code)

            if winner:
                game.winning_role = winner
                game.status = "finished"
                db.session.commit()
                emit("game_over", {
                    "winning_role": winner,
                    "secret_word": game.secret_word,
                    "players": _serialize_players(game.game_id),
                }, room=room_code)
            else:
                game.round_number += 1
                game.phase = "clue"
                db.session.commit()
                emit("phase_changed", {"phase": "clue", "round": game.round_number}, room=room_code)
