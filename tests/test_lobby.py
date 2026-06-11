"""Tests for the Imposter lobby system (HTTP + SocketIO)."""

import json
import secrets

from models import Game, Player, ChatMessage, Round, Vote
from game_logic import assign_roles


# ─── HTTP Route Tests ───────────────────────────────────────────────

class TestHTTPRoutes:
    def test_home_page(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"IMPOSTER" in resp.data

    def test_login_valid_name(self, client):
        resp = client.post("/login", data={"player_name": "Alice"}, follow_redirects=True)
        assert resp.status_code == 200
        assert b"hub" in resp.data or b"Create Room" in resp.data

    def test_login_empty_name(self, client):
        resp = client.post("/login", data={"player_name": ""}, follow_redirects=True)
        assert resp.status_code == 200
        assert b"valid name" in resp.data

    def test_login_invalid_name(self, client):
        resp = client.post("/login", data={"player_name": "<script>"}, follow_redirects=True)
        assert resp.status_code == 200
        assert b"valid name" in resp.data

    def test_login_xss_attack(self, client):
        resp = client.post("/login", data={"player_name": "<img onerror=alert(1) src=x>"}, follow_redirects=True)
        assert resp.status_code == 200
        assert b"valid name" in resp.data

    def test_login_sql_injection(self, client):
        resp = client.post("/login", data={"player_name": "Robert'; DROP TABLE players;--"}, follow_redirects=True)
        assert resp.status_code == 200
        assert b"valid name" in resp.data

    def test_hub_requires_login(self, client):
        resp = client.get("/hub", follow_redirects=True)
        assert resp.status_code == 200
        assert b"IMPOSTER" in resp.data

    def test_create_room(self, client):
        client.post("/login", data={"player_name": "Alice"})
        resp = client.post("/room/create", follow_redirects=True)
        assert resp.status_code == 200
        assert b"Lobby" in resp.data or b"Room:" in resp.data

    def test_create_and_join_room(self, client):
        # Creator logs in and creates a room
        client.post("/login", data={"player_name": "Alice"})
        resp = client.post("/room/create", follow_redirects=True)
        assert resp.status_code == 200

        # Extract room code from response
        import re
        match = re.search(rb"Room:\s*([A-Z0-9]+)", resp.data)
        assert match, "Room code not found in response"
        room_code = match.group(1).decode()

        # Second client joins
        client2 = client.application.test_client()
        resp2 = client2.post("/room/join", data={
            "room_code": room_code,
            "player_name": "Bob"
        }, follow_redirects=True)
        assert resp2.status_code == 200
        assert b"Lobby" in resp2.data or b"Players" in resp2.data

    def test_join_nonexistent_room(self, client):
        resp = client.post("/room/join", data={
            "room_code": "XXXXXX",
            "player_name": "Alice"
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Room not found" in resp.data or b"IMPOSTER" in resp.data


# ─── Local Game (Pass-and-Play) Route Tests ──────────────────────────

class TestLocalGameRoutes:
    def test_setup_page(self, client):
        resp = client.get("/game/setup")
        assert resp.status_code == 200
        assert b"Local Game Setup" in resp.data

    def test_setup_too_few_players(self, client):
        resp = client.post("/game/setup", data={
            "player_name": ["Alice", "Bob"],
            "imposter_count": 1,
            "jester_count": 0,
            "jester_info": "nothing",
            "category": "Animals",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"At least 3 players" in resp.data

    def test_setup_creates_game(self, client):
        resp = client.post("/game/setup", data={
            "player_name": ["Alice", "Bob", "Charlie"],
            "imposter_count": 1,
            "jester_count": 0,
            "jester_info": "nothing",
            "category": "Animals",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Round 1" in resp.data or b"Phase:" in resp.data

    def test_game_view_and_clue_submit(self, client):
        resp = client.post("/game/setup", data={
            "player_name": ["Alice", "Bob", "Charlie"],
            "imposter_count": 1,
            "jester_count": 0,
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Round 1" in resp.data

        with client.session_transaction() as sess:
            gid = sess.get("game_id")
        assert gid is not None

        from models import Player
        from extensions import db
        with client.application.app_context():
            player = Player.query.filter_by(game_id=gid).first()
            assert player is not None
            pid = player.player_id

        resp = client.post(f"/game/{gid}/clue", data={
            "player_id": pid, "clue": "ocean"
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_vote_local(self, client):
        resp = client.post("/game/setup", data={
            "player_name": ["Alice", "Bob", "Charlie"],
            "imposter_count": 1,
            "jester_count": 0,
        }, follow_redirects=True)
        assert resp.status_code == 200

        with client.session_transaction() as sess:
            gid = sess.get("game_id")
        assert gid is not None

        from models import Player
        from extensions import db
        with client.application.app_context():
            players = Player.query.filter_by(game_id=gid).order_by(Player.player_id).all()
            voter = players[0]
            target = players[1]

            resp = client.post(f"/game/{gid}/vote", data={
                "voter_id": voter.player_id,
                "target_id": target.player_id,
            }, follow_redirects=True)
            assert resp.status_code == 200


# ─── Game Logic Tests ───────────────────────────────────────────────

class TestGameLogic:
    def test_assign_roles_basic(self):
        players = [
            {"name": "A"}, {"name": "B"}, {"name": "C"},
            {"name": "D"}, {"name": "E"}, {"name": "F"},
        ]
        result = assign_roles(players, 1, 1)
        roles = [p["role"] for p in result]
        assert roles.count("imposter") == 1
        assert roles.count("jester") == 1
        assert roles.count("crewmate") == 4

    def test_assign_roles_too_few_players(self):
        players = [{"name": "A"}, {"name": "B"}]
        result = assign_roles(players, 3, 2)
        roles = [p["role"] for p in result]
        assert roles.count("imposter") == 2  # capped at n
        assert "jester" not in roles

    def test_assign_roles_no_jester(self):
        players = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        result = assign_roles(players, 1, 0)
        roles = [p["role"] for p in result]
        assert roles.count("imposter") == 1
        assert roles.count("jester") == 0
        assert roles.count("crewmate") == 2

    def test_assign_roles_all_imposter(self):
        players = [{"name": "A"}, {"name": "B"}]
        result = assign_roles(players, 2, 0)
        roles = [p["role"] for p in result]
        assert roles.count("imposter") == 2


# ─── SocketIO Event Tests ───────────────────────────────────────────

class TestSocketIOEvents:
    def _create_room(self, app):
        """Helper: create room via DB directly, return room_code, host_token, game_id."""
        from room_manager import create_room as cr
        from extensions import db
        host_token = secrets.token_urlsafe(32)
        game = cr()
        player = Player(game_id=game.game_id, player_token=host_token, name="Host", color="#7c3aed", role="crewmate")
        db.session.add(player)
        db.session.commit()
        game.creator_player_id = player.player_id
        db.session.commit()
        return game.room_code, host_token, game.game_id

    def test_join_room_event(self, app, socketio_client):
        with app.app_context():
            rc, token, gid = self._create_room(app)

        socketio_client.emit("join_room", {"room_code": rc, "player_token": token})
        received = socketio_client.get_received()
        events = [e["name"] for e in received]
        assert "players_updated" in events

    def test_chat_message(self, app, socketio_client):
        with app.app_context():
            rc, token, gid = self._create_room(app)

        socketio_client.emit("join_room", {"room_code": rc, "player_token": token})
        socketio_client.get_received()

        socketio_client.emit("chat_message", {
            "room_code": rc, "player_token": token, "message": "Hello!"
        })
        received = socketio_client.get_received()
        chat_events = [e for e in received if e["name"] == "chat_message"]
        assert len(chat_events) >= 1
        assert chat_events[-1]["args"][0]["message"] == "Hello!"

    def test_chat_xss_blocked(self, app, socketio_client):
        with app.app_context():
            rc, token, gid = self._create_room(app)

        socketio_client.emit("join_room", {"room_code": rc, "player_token": token})
        socketio_client.get_received()

        socketio_client.emit("chat_message", {
            "room_code": rc, "player_token": token, "message": "<script>alert('xss')</script>"
        })
        received = socketio_client.get_received()
        chat_events = [e for e in received if e["name"] == "chat_message"]
        assert len(chat_events) == 0

    def test_toggle_ready(self, app, socketio_client):
        with app.app_context():
            rc, token, gid = self._create_room(app)

        socketio_client.emit("join_room", {"room_code": rc, "player_token": token})
        socketio_client.get_received()

        socketio_client.emit("toggle_ready", {"room_code": rc, "player_token": token})
        received = socketio_client.get_received()
        update_events = [e for e in received if e["name"] == "players_updated"]
        assert len(update_events) >= 1

        players = update_events[-1]["args"][0]["players"]
        host = next(p for p in players if p["name"] == "Host")
        assert host["is_ready"] is True

    def test_add_ai_bot(self, app, socketio_client):
        with app.app_context():
            rc, token, gid = self._create_room(app)

        socketio_client.emit("join_room", {"room_code": rc, "player_token": token})
        socketio_client.get_received()

        socketio_client.emit("add_ai_bot", {"room_code": rc, "player_token": token})
        received = socketio_client.get_received()
        update_events = [e for e in received if e["name"] == "players_updated"]
        assert len(update_events) >= 1

        players = update_events[-1]["args"][0]["players"]
        bots = [p for p in players if p["is_bot"]]
        assert len(bots) == 1
        assert "AI Bot" in bots[0]["name"]

    def test_add_ai_bot_not_creator(self, app, socketio_client):
        with app.app_context():
            rc, token, gid = self._create_room(app)

        fake_token = secrets.token_urlsafe(32)
        socketio_client.emit("join_room", {"room_code": rc, "player_token": fake_token})
        socketio_client.get_received()

        socketio_client.emit("add_ai_bot", {"room_code": rc, "player_token": fake_token})
        received = socketio_client.get_received()
        update_events = [e for e in received if e["name"] == "players_updated"]
        assert len(update_events) == 0

    def test_start_game(self, app, socketio_client):
        with app.app_context():
            rc, token, gid = self._create_room(app)

        socketio_client.emit("join_room", {"room_code": rc, "player_token": token})
        socketio_client.get_received()

        socketio_client.emit("start_game", {"room_code": rc, "player_token": token})
        received = socketio_client.get_received()
        events = {e["name"] for e in received}
        assert "game_starting" in events
        assert "your_role" in events

    def test_start_game_not_creator(self, app, socketio_client):
        with app.app_context():
            rc, token, gid = self._create_room(app)

        fake_token = secrets.token_urlsafe(32)
        socketio_client.emit("join_room", {"room_code": rc, "player_token": fake_token})
        socketio_client.get_received()

        socketio_client.emit("start_game", {"room_code": rc, "player_token": fake_token})
        received = socketio_client.get_received()
        assert len(received) == 0

    def test_update_settings(self, app, socketio_client):
        with app.app_context():
            rc, token, gid = self._create_room(app)

        socketio_client.emit("join_room", {"room_code": rc, "player_token": token})
        socketio_client.get_received()

        socketio_client.emit("update_settings", {
            "room_code": rc,
            "player_token": token,
            "settings": {"imposter_count": 2, "jester_count": 1, "jester_info": "category", "category": "Food"}
        })
        received = socketio_client.get_received()
        settings_events = [e for e in received if e["name"] == "settings_updated"]
        assert len(settings_events) >= 1
        settings = settings_events[-1]["args"][0]
        assert settings["imposter_count"] == 2
        assert settings["jester_count"] == 1

    def test_full_game_flow(self, app, socketio_client):
        from extensions import db as _db

        with app.app_context():
            rc, token, gid = self._create_room(app)

            bot = Player(game_id=gid, player_token=secrets.token_urlsafe(32), name="Bot1", color="#333", role="crewmate", is_bot=True, is_connected=True)
            bob = Player(game_id=gid, player_token=secrets.token_urlsafe(32), name="Bob", color="#00f", role="crewmate")
            _db.session.add(bot)
            _db.session.add(bob)
            _db.session.commit()

        socketio_client.emit("join_room", {"room_code": rc, "player_token": token})
        socketio_client.get_received()

        socketio_client.emit("start_game", {"room_code": rc, "player_token": token})
        received = socketio_client.get_received()
        assert "game_starting" in {e["name"] for e in received}

        with app.app_context():
            game = Game.query.get(gid)
            game.phase = "clue"
            _db.session.commit()

        socketio_client.get_received()
        socketio_client.emit("submit_clue", {"room_code": rc, "player_token": token, "clue": "ocean"})
        received = socketio_client.get_received()
        clue_events = [e for e in received if e["name"] == "clue_submitted"]
        assert len(clue_events) >= 1
        assert clue_events[-1]["args"][0]["clue"] == "ocean"

        with app.app_context():
            bob = Player.query.filter_by(name="Bob").first()
            bob_id = bob.player_id

        socketio_client.get_received()

        with app.app_context():
            game = Game.query.get(gid)
            game.phase = "vote"
            _db.session.commit()

        socketio_client.emit("cast_vote", {"room_code": rc, "player_token": token, "target_id": bob_id})
        received = socketio_client.get_received()
        vote_events = [e for e in received if e["name"] == "vote_cast"]
        assert len(vote_events) >= 1


# ─── Security Tests ─────────────────────────────────────────────────

class TestSecurity:
    def _create_room(self, app):
        from extensions import db
        from room_manager import create_room as cr
        import secrets
        token = secrets.token_urlsafe(32)
        game = cr()
        player = Player(game_id=game.game_id, player_token=token, name="Host", color="#7c3aed", role="crewmate")
        db.session.add(player)
        db.session.commit()
        game.creator_player_id = player.player_id
        db.session.commit()
        return game.room_code, token, game.game_id

    def test_rate_limiting(self, app, socketio_client):
        with app.app_context():
            rc, token, gid = self._create_room(app)

        socketio_client.emit("join_room", {"room_code": rc, "player_token": token})
        socketio_client.get_received()

        for i in range(20):
            socketio_client.emit("chat_message", {
                "room_code": rc, "player_token": token, "message": f"msg {i}"
            })

        received = socketio_client.get_received()
        chat_events = [e for e in received if e["name"] == "chat_message"]
        assert len(chat_events) < 20

    def test_empty_clue_rejected(self, app, socketio_client):
        with app.app_context():
            rc, token, gid = self._create_room(app)

        socketio_client.emit("join_room", {"room_code": rc, "player_token": token})
        socketio_client.get_received()

        socketio_client.emit("submit_clue", {"room_code": rc, "player_token": token, "clue": ""})
        received = socketio_client.get_received()
        assert len(received) == 0

    def test_duplicate_clue_rejected(self, app, socketio_client):
        from extensions import db as _db
        with app.app_context():
            rc, token, gid = self._create_room(app)
            game = Game.query.get(gid)
            game.phase = "clue"
            _db.session.commit()

        socketio_client.emit("join_room", {"room_code": rc, "player_token": token})
        socketio_client.get_received()

        socketio_client.emit("submit_clue", {"room_code": rc, "player_token": token, "clue": "ocean"})
        socketio_client.get_received()

        socketio_client.emit("submit_clue", {"room_code": rc, "player_token": token, "clue": "beach"})
        received = socketio_client.get_received()
        clue_events = [e for e in received if e["name"] == "clue_submitted"]
        assert len(clue_events) == 0

    def test_xss_in_clue_rejected(self, app, socketio_client):
        with app.app_context():
            rc, token, gid = self._create_room(app)
            from extensions import db as _db
            game = Game.query.get(gid)
            game.phase = "clue"
            _db.session.commit()

        socketio_client.emit("join_room", {"room_code": rc, "player_token": token})
        socketio_client.get_received()

        socketio_client.emit("submit_clue", {
            "room_code": rc, "player_token": token, "clue": "<script>alert(1)</script>"
        })
        received = socketio_client.get_received()
        clue_events = [e for e in received if e["name"] == "clue_submitted"]
        assert len(clue_events) == 0
