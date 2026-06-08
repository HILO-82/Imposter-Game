from flask import request, session
from flask_socketio import emit, join_room, leave_room

from extensions import db
from models import Player, Game


def register_socketio_events(socketio):
    """Register all SocketIO event handlers."""

    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        print(f"Client connected: {request.sid}")

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        print(f"Client disconnected: {request.sid}")
        
        # Mark player as disconnected if they were in a room
        room_code = session.get('room_code')
        if room_code:
            player_name = session.get('player_name')
            if player_name:
                game = Game.query.filter_by(room_code=room_code).first()
                if game:
                    player = Player.query.filter_by(
                        game_id=game.game_id,
                        name=player_name
                    ).first()
                    if player:
                        player.is_connected = False
                        db.session.commit()
                        emit('player_disconnected', {
                            'player_name': player_name,
                            'room_code': room_code
                        }, room=room_code)

    @socketio.on('join_room')
    def handle_join_room(data):
        """Handle player joining a room."""
        room_code = data.get('room_code')
        player_name = data.get('player_name')
        
        if room_code:
            join_room(room_code)
            session['room_code'] = room_code
            session['player_name'] = player_name
            
            emit('player_joined', {
                'player_name': player_name,
                'room_code': room_code
            }, room=room_code)

    @socketio.on('leave_room')
    def handle_leave_room(data):
        """Handle player leaving a room."""
        room_code = data.get('room_code')
        if room_code:
            leave_room(room_code)
            
            player_name = session.get('player_name')
            if player_name:
                emit('player_left', {
                    'player_name': player_name,
                    'room_code': room_code
                }, room=room_code)

    @socketio.on('start_game')
    def handle_start_game(data):
        """Handle game start."""
        room_code = data.get('room_code')
        if room_code:
            game = Game.query.filter_by(room_code=room_code).first()
            if game:
                game.phase = 'role_reveal'
                game.status = 'active'
                db.session.commit()
                
                emit('game_started', {
                    'room_code': room_code,
                    'phase': 'role_reveal'
                }, room=room_code)

    @socketio.on('submit_clue')
    def handle_submit_clue(data):
        """Handle clue submission."""
        room_code = data.get('room_code')
        clue = data.get('clue')
        player_name = data.get('player_name')
        
        if room_code and clue:
            emit('clue_submitted', {
                'player_name': player_name,
                'clue': clue,
                'room_code': room_code
            }, room=room_code)

    @socketio.on('submit_vote')
    def handle_submit_vote(data):
        """Handle vote submission."""
        room_code = data.get('room_code')
        voter_name = data.get('voter_name')
        target_name = data.get('target_name')
        
        if room_code and voter_name and target_name:
            emit('vote_submitted', {
                'voter_name': voter_name,
                'target_name': target_name,
                'room_code': room_code
            }, room=room_code)

    @socketio.on('clue_submitted')
    def handle_clue_submitted(data):
        """Broadcast clue submission to all players in room."""
        room_code = data.get('room_code')
        clue = data.get('clue')
        player = data.get('player')
        
        if room_code and clue and player:
            emit('new_clue', {
                'room_code': room_code,
                'clue': clue,
                'player': player
            }, room=room_code)

    @socketio.on('vote_submitted')
    def handle_vote_submitted(data):
        """Broadcast vote submission to all players in room."""
        room_code = data.get('room_code')
        voter = data.get('voter')
        target = data.get('target')
        
        if room_code and voter and target:
            emit('new_vote', {
                'room_code': room_code,
                'voter': voter,
                'target': target
            }, room=room_code)
