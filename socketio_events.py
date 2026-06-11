from flask import request, session
from flask_socketio import emit, join_room

from extensions import db
from models import Game, Player, Round, Vote, ChatMessage
from game_logic import assign_roles, alive_players, all_clues_submitted, tally_votes, eliminate_top_voted, check_win_condition
from security import validate_player_name, validate_clue, validate_message, rate_limit, strip_html


def _serialize_players(game_id):
    players = Player.query.filter_by(game_id=game_id).order_by(Player.player_id).all()
    return [
        {
            "player_id": p.player_id,
            "name": p.name,
            "color": p.color,
            "is_bot": p.is_bot,
            "is_connected": p.is_connected,
            "is_ready": p.is_ready,
            "was_voted_out": p.was_voted_out,
            "role": p.role,
        }
        for p in players
    ]


def _serialize_chat(game_id):
    messages = ChatMessage.query.filter_by(game_id=game_id).order_by(ChatMessage.timestamp).all()
    return [
        {
            "player_name": m.player.name,
            "player_color": m.player.color,
            "message": m.content,
            "timestamp": m.timestamp.isoformat(),
        }
        for m in messages
    ]


def register_socketio_events(socketio):

    @socketio.on("connect")
    def handle_connect():
        pass

    @socketio.on("disconnect")
    def handle_disconnect():
        room_code = session.get("room_code")
        player_token = session.get("player_token")
        if not room_code or not player_token:
            return
        game = Game.query.filter_by(room_code=room_code).first()
        if not game:
            return
        player = Player.query.filter_by(game_id=game.game_id, player_token=player_token).first()
        if player:
            player.is_connected = False
            db.session.commit()
            emit("players_updated", {"players": _serialize_players(game.game_id)}, room=room_code)

    @socketio.on("join_room")
    def handle_join_room(data):
        room_code = data.get("room_code")
        player_token = data.get("player_token")
        if not room_code or not player_token:
            return
        game = Game.query.filter_by(room_code=room_code).first()
        player = Player.query.filter_by(game_id=game.game_id, player_token=player_token).first()
        if not game or not player:
            return

        join_room(room_code)
        join_room(player_token)
        session["room_code"] = room_code
        session["player_token"] = player_token

        player.is_connected = True
        db.session.commit()

        emit("players_updated", {"players": _serialize_players(game.game_id)}, room=room_code)

    @socketio.on("chat_message")
    def handle_chat_message(data):
        if not rate_limit(request.sid):
            return
        room_code = data.get("room_code")
        player_token = data.get("player_token")
        raw = data.get("message", "").strip()

        if not room_code or not player_token or not validate_message(raw):
            return
        content = strip_html(raw)
        game = Game.query.filter_by(room_code=room_code).first()
        player = Player.query.filter_by(game_id=game.game_id, player_token=player_token).first()
        if not game or not player:
            return

        msg = ChatMessage(game_id=game.game_id, player_id=player.player_id, content=content)
        db.session.add(msg)
        db.session.commit()

        emit("chat_message", {
            "player_name": player.name,
            "player_color": player.color,
            "message": content,
            "timestamp": msg.timestamp.isoformat(),
        }, room=room_code)

    @socketio.on("toggle_ready")
    def handle_toggle_ready(data):
        room_code = data.get("room_code")
        player_token = data.get("player_token")
        if not room_code or not player_token:
            return
        game = Game.query.filter_by(room_code=room_code).first()
        player = Player.query.filter_by(game_id=game.game_id, player_token=player_token).first()
        if not game or not player:
            return

        player.is_ready = not player.is_ready
        db.session.commit()
        emit("players_updated", {"players": _serialize_players(game.game_id)}, room=room_code)

    @socketio.on("add_ai_bot")
    def handle_add_ai_bot(data):
        room_code = data.get("room_code")
        player_token = data.get("player_token")
        if not room_code or not player_token:
            return
        game = Game.query.filter_by(room_code=room_code).first()
        player = Player.query.filter_by(game_id=game.game_id, player_token=player_token).first()
        if not game or not player or player.player_id != game.creator_player_id:
            return

        count = Player.query.filter_by(game_id=game.game_id).count()
        bot = Player(
            game_id=game.game_id,
            name=f"AI Bot {count}",
            color="#6b7280",
            role="crewmate",
            is_bot=True,
            is_connected=True,
            is_ready=True,
        )
        db.session.add(bot)
        db.session.commit()
        emit("players_updated", {"players": _serialize_players(game.game_id)}, room=room_code)

    @socketio.on("update_settings")
    def handle_update_settings(data):
        room_code = data.get("room_code")
        player_token = data.get("player_token")
        if not room_code or not player_token:
            return
        game = Game.query.filter_by(room_code=room_code).first()
        player = Player.query.filter_by(game_id=game.game_id, player_token=player_token).first()
        if not game or not player or player.player_id != game.creator_player_id:
            return

        s = data.get("settings", {})
        if "imposter_count" in s:
            game.imposter_count = max(1, min(4, int(s["imposter_count"])))
        if "jester_count" in s:
            game.jester_count = max(0, min(2, int(s["jester_count"])))
        if "jester_info" in s:
            game.jester_info = s["jester_info"]
        if "secret_word" in s and s["secret_word"]:
            game.secret_word = s["secret_word"]
        if "category" in s:
            game.category = s["category"]
        db.session.commit()

        emit("settings_updated", {
            "imposter_count": game.imposter_count,
            "jester_count": game.jester_count,
            "jester_info": game.jester_info,
            "category": game.category,
        }, room=room_code)

    @socketio.on("start_game")
    def handle_start_game(data):
        room_code = data.get("room_code")
        player_token = data.get("player_token")
        if not room_code or not player_token:
            return
        game = Game.query.filter_by(room_code=room_code).first()
        player = Player.query.filter_by(game_id=game.game_id, player_token=player_token).first()
        if not game or not player or player.player_id != game.creator_player_id:
            return

        players = Player.query.filter_by(game_id=game.game_id).all()
        if len(players) < 1:
            return

        player_data = [
            {"name": p.name, "color": p.color, "role": "crewmate", "is_bot": p.is_bot}
            for p in players
        ]
        assigned = assign_roles(player_data, game.imposter_count, game.jester_count)
        for i, p in enumerate(players):
            p.role = assigned[i]["role"]

        game.phase = "role_reveal"
        game.status = "roles"
        game.round_number = 1
        db.session.commit()

        emit("game_starting", {"room_code": room_code}, room=room_code)

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

            emit("your_role", role_data, room=p.player_token)

    @socketio.on("submit_clue")
    def handle_submit_clue(data):
        room_code = data.get("room_code")
        player_token = data.get("player_token")
        raw_clue = data.get("clue", "").strip()

        if not room_code or not player_token or not validate_clue(raw_clue):
            return
        clue = strip_html(raw_clue)
        game = Game.query.filter_by(room_code=room_code).first()
        if not game or game.phase != "clue":
            return
        player = Player.query.filter_by(game_id=game.game_id, player_token=player_token).first()
        if not player or player.was_voted_out or player.is_bot:
            return

        existing = Round.query.filter_by(
            game_id=game.game_id, round_number=game.round_number, player_id=player.player_id
        ).first()
        if existing:
            return

        db.session.add(Round(
            game_id=game.game_id,
            round_number=game.round_number,
            clue_given=clue,
            player_id=player.player_id,
        ))
        db.session.commit()

        emit("clue_submitted", {
            "player_name": player.name,
            "clue": clue,
        }, room=room_code)

        if all_clues_submitted(game):
            game.phase = "vote"
            db.session.commit()
            emit("phase_changed", {"phase": "vote", "round": game.round_number}, room=room_code)

    @socketio.on("cast_vote")
    def handle_cast_vote(data):
        room_code = data.get("room_code")
        player_token = data.get("player_token")
        target_id = data.get("target_id")

        if not room_code or not player_token or not target_id:
            return
        game = Game.query.filter_by(room_code=room_code).first()
        if not game or game.phase != "vote":
            return

        voter = Player.query.filter_by(game_id=game.game_id, player_token=player_token).first()
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

        emit("vote_cast", {"player_name": voter.name}, room=room_code)

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
