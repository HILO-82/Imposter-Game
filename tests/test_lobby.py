"""Tests for Imposter game (single-device + game logic)."""

import json
import secrets

from models import Game, Player, Round, Vote
from game_logic import assign_roles


class TestHTTPRoutes:
    def test_home_page(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"IMPOSTER" in resp.data

    def test_home_has_buttons(self, client):
        resp = client.get("/")
        assert b"Single Device" in resp.data
        assert b"Multi Device" in resp.data
        assert b"Settings" in resp.data

    def test_settings_page(self, client):
        resp = client.get("/settings")
        assert resp.status_code == 200
        assert b"Settings" in resp.data


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
        assert b"Role Assignment" in resp.data or b"role" in resp.data.lower()

    def test_game_view_and_clue_submit(self, client):
        resp = client.post("/game/setup", data={
            "player_name": ["Alice", "Bob", "Charlie"],
            "imposter_count": 1,
            "jester_count": 0,
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Role Assignment" in resp.data

        with client.session_transaction() as sess:
            gid = sess.get("game_id")
        assert gid is not None

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
        assert roles.count("imposter") == 2

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


class TestMultiDeviceSetup:
    def test_multi_setup_page(self, client):
        resp = client.get("/multi-device/host")
        assert resp.status_code == 200
        assert b"Multi-Device" in resp.data

    def test_multi_create_game(self, client):
        resp = client.post("/multi-device/host", data={
            "player_name": ["Player 1", "Player 2", "Player 3"],
            "imposter_count": 1,
            "jester_count": 0,
            "jester_info": "nothing",
            "category": "Animals",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Multi-Device Game" in resp.data or b"Scan to Join" in resp.data


class TestSocketIOEvents:
    def _create_multi_game(self, app):
        from room_manager import generate_room_code
        from extensions import db
        from game_logic import assign_roles
        from words import random_word

        code = generate_room_code()
        host_token = secrets.token_urlsafe(32)
        word_obj = random_word("Animals")
        game = Game(
            room_code=code,
            num_players=3,
            imposter_count=1,
            jester_count=0,
            secret_word=word_obj["word"],
            category="Animals",
            status="lobby",
            phase="lobby",
            is_multi_device=True,
            host_token=host_token,
        )
        db.session.add(game)
        db.session.flush()

        for i, name in enumerate(["Alice", "Bob", "Charlie"]):
            token = None if i > 0 else secrets.token_urlsafe(32)
            player = Player(
                game_id=game.game_id,
                player_token=token,
                name=name,
                role="crewmate",
                color=["#7c3aed", "#10b981", "#f59e0b"][i],
            )
            db.session.add(player)
        db.session.commit()
        return code, host_token, game.game_id

    def test_multi_join_flow(self, app, client):
        """Test the HTTP multi-device join flow."""
        resp = client.post("/multi-device/host", data={
            "player_name": ["Player 1", "Player 2", "Player 3"],
            "imposter_count": 1,
            "jester_count": 0,
            "jester_info": "nothing",
            "category": "Animals",
        }, follow_redirects=True)
        assert resp.status_code == 200
        # Extract room code from QR URL
        import re
        match = re.search(rb"/multi-device/join/([A-Z0-9]+)", resp.data)
        assert match, "Join URL not found"
        code = match.group(1).decode()

        resp2 = client.get(f"/multi-device/join/{code}")
        assert resp2.status_code == 200
        assert b"Join Game" in resp2.data

        resp3 = client.post(f"/multi-device/join/{code}", data={
            "name": "Alice"
        }, follow_redirects=True)
        # Should redirect to play page
        assert resp3.status_code == 200
        assert b"Waiting for host" in resp3.data or b"IMPOSTER" in resp3.data or b"CREWMATE" in resp3.data

    def test_empty_clue_rejected(self, app, socketio_client):
        with app.app_context():
            rc, token, gid = self._create_multi_game(app)
            game = Game.query.get(gid)
            game.phase = "clue"
            from extensions import db as _db
            _db.session.commit()

        socketio_client.emit("join_game", {
            "room_code": rc, "token": token, "is_host": False
        })
        socketio_client.get_received()

        socketio_client.emit("submit_clue", {
            "room_code": rc, "token": token, "clue": ""
        })
        received = socketio_client.get_received()
        assert len(received) == 0

    def test_duplicate_clue_rejected(self, app, socketio_client):
        from extensions import db as _db
        with app.app_context():
            rc, token, gid = self._create_multi_game(app)
            game = Game.query.get(gid)
            game.phase = "clue"
            _db.session.commit()

        socketio_client.emit("join_game", {
            "room_code": rc, "token": token, "is_host": False
        })
        socketio_client.get_received()

        socketio_client.emit("submit_clue", {
            "room_code": rc, "token": token, "clue": "ocean"
        })
        socketio_client.get_received()

        socketio_client.emit("submit_clue", {
            "room_code": rc, "token": token, "clue": "beach"
        })
        received = socketio_client.get_received()
        clue_events = [e for e in received if e["name"] == "clue_submitted"]
        assert len(clue_events) == 0

    def test_xss_in_clue_rejected(self, app, socketio_client):
        from extensions import db as _db
        with app.app_context():
            rc, token, gid = self._create_multi_game(app)
            game = Game.query.get(gid)
            game.phase = "clue"
            _db.session.commit()

        socketio_client.emit("join_game", {
            "room_code": rc, "token": token, "is_host": False
        })
        socketio_client.get_received()

        socketio_client.emit("submit_clue", {
            "room_code": rc, "token": token, "clue": "<script>alert(1)</script>"
        })
        received = socketio_client.get_received()
        clue_events = [e for e in received if e["name"] == "clue_submitted"]
        assert len(clue_events) == 0
