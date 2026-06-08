# Online Multiplayer Implementation Plan

## Overview
Convert the current single-device Flask app to support multiple players connecting from different computers in real-time.

## Required Changes

### 1. Real-time Communication Layer
- **Task**: Implement WebSocket support for real-time bidirectional communication
- **Details**: 
  - Install and configure Flask-SocketIO or similar WebSocket library
  - Replace HTTP polling with WebSocket events for game state updates
  - Handle connection/disconnection events
- **Files to modify**: app.py, requirements.txt

### 2. Game State Storage
- **Task**: Move game state from session to database/shared storage
- **Details**:
  - Create database models for Game, Player, GameSession
  - Store game state in database instead of Flask sessions
  - Implement game room/lobby system with unique room codes
- **Files to modify**: models.py, create new models
- **New files**: Possibly a game_state.py module

### 3. Room/Lobby System
- **Task**: Create a lobby system where players can join rooms
- **Details**:
  - Generate unique room codes (e.g., 6-character codes)
  - Allow players to create rooms and become host
  - Allow other players to join rooms by code
  - Display list of players in lobby
  - Host controls game start
- **Files to modify**: routes/lobby.py, templates/index.html
- **New templates**: lobby.html or add to existing

### 4. Player Identification
- **Task**: Implement player identification system
- **Details**:
  - Generate unique player IDs for each connection
  - Allow players to set their name when joining
  - Track which player is which across connections
  - Handle reconnection scenarios
- **Files to modify**: routes/lobby.py, possibly create player.py module

### 5. Synchronized Game Phases
- **Task**: Ensure all clients see the same game phase
- **Details**:
  - Broadcast phase changes to all connected clients in a room
  - Sync role reveal phase across all players
  - Sync voting phase results
  - Handle player disconnections mid-game
- **Files to modify**: routes/game.py, routes/lobby.py, templates/game.html

### 6. Real-time Clue System
- **Task**: Implement real-time clue submission and display
- **Details**:
  - Allow players to submit clues via WebSocket
  - Broadcast clues to all players in room
  - Display clues in real-time on all clients
  - Implement AI bot clue generation
- **Files to modify**: routes/game.py, ml/word_bot.py, templates/game.html

### 7. Real-time Voting System
- **Task**: Implement real-time voting with live results
- **Details**:
  - Allow players to vote for elimination
  - Broadcast vote counts in real-time
  - Display voting progress to all players
  - Handle vote completion and elimination
- **Files to modify**: routes/game.py, templates/game.html

### 8. AI Bot Integration
- **Task**: Make AI bots work in multiplayer context
- **Details**:
  - AI bots should automatically submit clues based on their role
  - AI bots should participate in voting
  - AI bot behavior should be synchronized across all clients
  - AI bot clues should use the word_bot.py module
- **Files to modify**: routes/game.py, ml/word_bot.py

### 9. Game State Synchronization
- **Task**: Ensure all clients have consistent game state
- **Details**:
  - Implement state reconciliation mechanism
  - Handle network latency and race conditions
  - Ensure atomic operations for game state changes
  - Implement game end detection and cleanup
- **Files to modify**: routes/game.py, possibly create game_sync.py module

### 10. Frontend Updates
- **Task**: Update templates to handle real-time updates
- **Details**:
  - Add SocketIO client library to templates
  - Implement JavaScript to handle WebSocket events
  - Update UI to show real-time updates without page refresh
  - Add connection status indicators
- **Files to modify**: templates/index.html, templates/game.html, base.html

### 11. Error Handling & Edge Cases
- **Task**: Handle disconnections, timeouts, and errors gracefully
- **Details**:
  - Handle player disconnection mid-game
  - Implement timeout for inactive players
  - Handle network errors gracefully
  - Provide reconnection mechanism
- **Files to modify**: routes/game.py, routes/lobby.py

### 12. Testing
- **Task**: Test multiplayer functionality
- **Details**:
  - Test with multiple browser windows
  - Test with actual different computers on same network
  - Test AI bot integration
  - Test edge cases (disconnections, timeouts)
- **Files to modify**: No specific files, manual testing

## Implementation Order
1. Real-time Communication Layer (WebSocket setup)
2. Game State Storage (database models)
3. Room/Lobby System (create/join rooms)
4. Player Identification (track players)
5. Frontend Updates (SocketIO client integration)
6. Synchronized Game Phases (broadcast phase changes)
7. Real-time Clue System (clue submission/broadcasting)
8. Real-time Voting System (voting with live results)
9. AI Bot Integration (bots in multiplayer)
10. Game State Synchronization (consistency)
11. Error Handling & Edge Cases (robustness)
12. Testing (validation)

## Dependencies to Add
- Flask-SocketIO (for WebSocket support)
- python-socketio (SocketIO server)
- eventlet or gevent (async WebSocket support)
