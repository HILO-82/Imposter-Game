# Database Schema — Imposter Game

## Entity-Relationship Diagram

```mermaid
erDiagram
    settings {
        int id PK "singleton (id=1)"
        int default_player_count   "validated 3-8"
        int default_imposter_count "validated 1-4"
        int default_jester_count   "validated 0-2"
        str default_jester_info    "nothing|category|partial|full"
        str default_category
        bool dark_mode
        int font_size
        bool high_contrast
        bool smart_assign
    }

    games {
        int game_id PK
        str room_code      "UK, IX  🔒 unique + indexed"
        datetime date
        int num_players     "🔒 validated min=3 max=8"
        int imposter_count  "🔒 validated min=1 max=4"
        int jester_count    "🔒 validated min=0 max=2"
        str jester_info     "nothing|category|partial|full"
        str winning_role    "nullable; crewmate|imposter|jester"
        str secret_word     "🔒 never sent to imposters (app-layer)"
        str category
        str status          "lobby|active|finished"
        int round_number
        str phase           "role_reveal|clue|vote"
        int current_player_index
        int creator_player_id
        bool is_multi_device
        str host_token      "UK, IX  🔒 unique + session-gated"
        str starter_player_name
    }

    players {
        int player_id PK
        int game_id FK
        str session_id      "IX  🔒 session-linked"
        str player_token    "UK, IX  🔒 unique + token-gated"
        str name            "🔒 regex-validated ^[\\w\\s\\-'.""]{1,50}$"
        str role            "crewmate|imposter|jester"
        str color
        bool was_voted_out
        bool is_bot
        bool is_connected
    }

    rounds {
        int round_id PK
        int game_id FK
        int round_number
        str clue_given      "🔒 max 100 chars, blocks SQL injection patterns"
        int player_id FK
    }

    votes {
        int vote_id PK
        int game_id FK
        int round_number
        int voter_id FK
        int target_id FK
    }

    game_events {
        int event_id PK
        int game_id FK
        int round_number
        int player_id FK "nullable"
        str event_type     "eliminated|imposter_out|jester_out|crewmate_out"
        text notes         "🔒 HTML-stripped via strip_html()"
    }

    words {
        int word_id PK
        str word       "UK  🔒 unique"
        int category_id
        int subcategory_id
        int word_length
        float commonality
    }

    games ||--o{ players : "has"
    games ||--o{ rounds : "contains"
    games ||--o{ votes : "contains"
    games ||--o{ game_events : "logs"
    players ||--o{ rounds : "submits"
    players ||--o{ votes : "casts as voter"
    players ||--o{ votes : "receives as target"
    players ||--o{ game_events : "involved in"
```

---

## Security Controls Applied

| Layer | Control | Where | What it protects |
|-------|---------|-------|------------------|
| **Schema** | `UNIQUE` constraint | `games.room_code`, `games.host_token`, `players.player_token`, `words.word` | Prevents duplicate tokens / room codes / words |
| **Schema** | `INDEX` | `games.room_code`, `games.host_token`, `players.player_token`, `players.session_id` | Fast lookup for join/auth queries |
| **Input** | Regex validation | `validate_player_name()` in `security.py:36` | Player names: `^[\w\s\-'.']{1,50}$` — no HTML, no special chars |
| **Input** | SQL injection block | `validate_clue()` in `security.py:43` | Blocks `<script`, `drop table`, `union select`, `--`, `/*` |
| **Input** | HTML stripping | `strip_html()` in `security.py:32` and `validate_message()` at `security.py:51` | Sanitises notes and chat messages |
| **Input** | Length limits | `Config.MAX_NAME_LENGTH=50`, `Config.MAX_CLUE_LENGTH=100`, message max=500 | Prevents oversized input attacks |
| **Input** | Positive integer check | `validate_positive_int()` in `security.py:60` | All numeric fields validated min/max |
| **Session** | Session ID check | `require_game_session()` / `game_session_required` decorator at `security.py:68-78` | Aborts 403 if `session.game_id` doesn't match route param |
| **Session** | Token-based auth | `host_token` and `player_token` checked in multi-device routes | Only the host with the correct token can access the dashboard |
| **Rate limit** | Sliding window | `rate_limit(sid)` in `security.py:21` | Max 10 SocketIO events/sec per connection |
| **App** | Secret key from env | `Config.SECRET_KEY` reads `os.environ.get("SECRET_KEY")` at `config.py:8` | Flask session signing; falls back to dev-only default |
| **App** | CORS | `cors_allowed_origins="*"` at `app.py:25` | SocketIO cross-origin (for multi-device mobile clients) |
