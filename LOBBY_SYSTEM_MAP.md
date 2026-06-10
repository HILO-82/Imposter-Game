# Imposter Lobby System — Code Map

**Note:** This map describes the target lobby system from scratch. Prior lobby code should be disregarded and rewritten to match this spec.

## Database Models

```
Game
  game_id, room_code (unique, 6-char), date
  secret_word, category
  imposter_count, jester_count, jester_info
  num_players (target), status (lobby|roles|playing|finished)
  round_number, phase (clue|vote)
  creator_player_id

Player
  player_id, game_id (FK)
  player_token (unique, per-session), name, color
  role (crewmate|imposter|jester), is_bot, is_connected
  is_ready, was_voted_out

Round
  round_id, game_id (FK), round_number
  player_id (FK), clue_given

Vote
  vote_id, game_id (FK), round_id (FK)
  voter_id (FK), target_id (FK)

ChatMessage
  message_id, game_id (FK), player_id (FK)
  content, timestamp
```

## Routes (HTTP — page navigation)

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/` | Enter name |
| POST | `/login` | Create session |
| GET | `/hub` | Player hub: Create Room / Join Room |
| POST | `/room/create` | Create room -> redirect to `/room/<code>` |
| POST | `/room/join` | Enter name + room code -> redirect to `/room/<code>` |
| GET | `/room/<code>` | Lobby page (renders with all state) |

## Lobby Page (`/room/<code>`)

Every player sees:
- Room code (to share)
- Player list (name, color, ready status, online indicator)
- Chat box (all players, real-time)

**Creator** additionally sees:
- Settings panel (imposter count, jester count, jester info, secret word/category)
- "Add AI Bot" button
- "Start Game" button (enabled when `players >= 1`)

## SocketIO Events (real-time)

### From Client:
- `join_room` — `{room_code, player_token}` — join the SocketIO room
- `chat_message` — `{room_code, player_token, message}`
- `toggle_ready` — `{room_code, player_token}`
- `add_ai_bot` — `{room_code}` (creator only)
- `update_settings` — `{room_code, settings}` (creator only)
- `start_game` — `{room_code}` (creator only)
- `submit_clue` — `{room_code, player_token, clue}`
- `cast_vote` — `{room_code, player_token, target_id}`

### From Server (broadcast to room):
- `players_updated` — full player list (after join/leave/ready/AI/add)
- `chat_message` — `{player_name, message}`
- `player_joined` — `{player_name, color}`
- `player_left` — `{player_name}`
- `player_ready` — `{player_name, is_ready}`
- `ai_bot_added` — `{bot_name}`
- `settings_updated` — `{settings}`
- `game_starting` — transitions all clients to role reveal
- `your_role` — **private** (only to that socket) — `{role, secret_word?, jester_info?}`
- `phase_changed` — `{phase}`
- `clue_submitted` — `{player_name, clue}`
- `vote_cast` — `{player_name}`
- `vote_results` — `{tally, eliminated_player}`
- `player_eliminated` — `{player_name}`
- `game_over` — `{winning_role, secret_word, players}`

## Game Flow

### 1. Enter Name -> Hub
User enters name, gets a `player_token` stored in session. Hub shows "Create Room" and "Join Room" options.

### 2. Create Room
POST creates a `Game` row with a 6-char code. Creator added as a `Player` row. Redirect to `/room/<code>`.

### 3. Join Room
Enter room code + name. `Player` row created with unique `player_token`. Redirect to `/room/<code>`.

### 4. In Lobby
- All connected sockets join the SocketIO room `<room_code>`
- Player list updates in real-time via `players_updated`
- Creator sees settings + "Add AI Bot" + "Start Game"
- Players use `toggle_ready` to mark ready

### 5. Start Game (creator)
- Server assigns roles (`assign_roles`), sets `status=roles`
- Server emits `game_starting` to the room
- Server sends each socket their **private** `your_role` event
- Front-end auto-navigates to role reveal screen

### 6. Role Reveal
- Each player sees their own role privately on their own device
- After viewing, they click "I'm Ready" -> `toggle_ready`
- When all ready -> server emits `phase_changed {phase: "playing"}`
- Front-end navigates to game screen

### 7. Game Screen (Round N)
- **Clue Phase:** Each alive player submits one clue
  - Clues broadcast to all via `clue_submitted`
- **Vote Phase:** All alive players vote for elimination
  - `vote_cast` shows someone voted (not their target)
  - When all votes in -> server tallies, emits `vote_results`
  - Eliminated player announced via `player_eliminated`
- **Next Round** or **Game Over**

### 8. Game Over
Server emits `game_over` with winning role and secret word revealed to all.

## Key Principles

- **Server is authority** — all game logic (role assignment, vote tallying, elimination, win check) happens server-side
- **SocketIO for real-time** — HTTP only for initial page loads; all game interactions flow through WebSocket events
- **No polling** — every state change is pushed from server to clients via events
- **Creator controls settings** — settings changes broadcast to all so the lobby UI stays in sync
- **No pass-and-play** — each player uses their own device with their own `player_token`
- **Chat is always available** — during lobby, role reveal, and game
