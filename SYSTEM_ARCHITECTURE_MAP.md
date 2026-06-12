# Imposter Game — Unified System Architecture Map

This document serves as the comprehensive, single source of truth for the Imposter Game's architecture, data models, workflows, security, and machine learning components. It consolidates information from all other planning and coursework files.

---

## 🏗️ 1. High-Level Architecture (Level 0 Context)

```
       +------------------+             +-----------------+
       |  Player Browser  |             |  PythonAnywhere |
       | (SocketIO & HTML)|             |   Web Server    |
       +--------+---------+             +--------+--------+
                |                                |
                | HTTP & WebSocket Sessions      | Runs Web App
                v                                v
       +------------------+             +-----------------+
       |    Flask App     | <=========> |   SQLite DB     |
       |  (app.py, WSGI)  |             |  (imposter.db)  |
       +--------+---------+             +-----------------+
                |
                +---> ML Inference (Loads models at startup)
                      |--> KNN Word Guessing Model (knn_model.pkl)
                      |--> LR Voting Model (lr_model.pkl)
```

The system is a real-time, multi-device, web-based social deduction game. Each player connects via their own browser to a centralized Flask server. Bi-directional, real-time events are managed with Flask-SocketIO.

---

## 🗄️ 2. Database Schema (models.py)

The game persists all state, player data, chat, clues, and votes in an SQLite database using the SQLAlchemy ORM.

```
+--------------------------------------------------------+
|                         GAMES                          |
+--------------------------------------------------------+
| game_id (PK, Integer)                                  |
| room_code (String(10), unique, index, e.g. "ABCDEF")   |
| date (DateTime, UTC default)                           |
| num_players (Integer, target count)                    |
| imposter_count (Integer, default 1)                    |
| jester_count (Integer, default 0)                      |
| jester_info (String(20), default "nothing")            |
| winning_role (String(20), nullable)                    |
| secret_word (String(100))                              |
| category (String(50))                                  |
| status (String(20), default "lobby")                   |
| round_number (Integer, default 1)                      |
| phase (String(20), default "lobby")                    |
| current_player_index (Integer, default 0)              |
| creator_player_id (Integer, nullable)                  |
+--------------------------------------------------------+
                           |
                           | 1 : Many (Cascade delete)
                           +-----------------------------------------------+
                           |                       |                       |
                           v                       v                       v
+--------------------------------------+ +-------------------+ +-------------------+
|               PLAYERS                | |      ROUNDS       | |       VOTES       |
+--------------------------------------+ +-------------------+ +-------------------+
| player_id (PK, Integer)              | | round_id (PK)     | | vote_id (PK)      |
| game_id (FK, Integer)                | | game_id (FK)      | | game_id (FK)      |
| session_id (String(100), index)      | | round_number (Int)| | round_number (Int)|
| player_token (String(100), unique)   | | player_id (FK)    | | voter_id (FK)     |
| name (String(50))                    | | clue_given (Str)  | | target_id (FK)    |
| role (String(20))                    | +-------------------+ +-------------------+
| color (String(10))                   |
| was_voted_out (Boolean)              | +-----------------------------------------+
| is_bot (Boolean)                     | |              CHAT_MESSAGES              |
| is_connected (Boolean)               | +-----------------------------------------+
| is_ready (Boolean)                   | | message_id (PK) | game_id (FK)          |
|                                      | | player_id (FK)  | content (String(500)) |
+--------------------------------------+ | timestamp       |                       |
                                         +-----------------------------------------+
```

### Word Dictionary Table
Used for KNN lookup and random game generation.
*   `words` table: `word_id` (PK), `word` (String, unique), `category_id` (Int), `subcategory_id` (Int), `word_length` (Int), `commonality` (Float).

---

## 🔀 3. System Interfaces & Routes

The application uses **HTTP** strictly for initial entry and setup, and **WebSockets (SocketIO)** for all real-time, interactive gameplay once inside a room.

### HTTP Routes

| Method | Route | Description |
| :--- | :--- | :--- |
| **GET** | `/` | Enter Name / Home Page |
| **POST** | `/login` | Creates player session & redirects to Hub |
| **GET** | `/hub` | Selection Screen: Create Room or Join Room |
| **POST** | `/room/create` | Generates new `Game` entry & 6-character room code |
| **POST** | `/room/join` | Adds new player to the game with chosen room code |
| **GET** | `/room/<code>`| Loads lobby/game page, validates player session |

### SocketIO Bidirectional Events

```
        Client                                                Server
          |                                                     |
          | ----> join_room(room_code, token) ----------------> | (Socket joins room)
          | <---- players_updated(player_list) ---------------- | (Broadcast updates)
          |                                                     |
          | ----> toggle_ready(room_code, token) -------------> | (Tracks ready status)
          |                                                     |
          | ----> [Creator Only] start_game(room_code) -------> | (Assigns roles/words)
          | <---- game_starting ------------------------------- | (Transitions clients)
          | <---- your_role (Private/Direct) ------------------ | (Sends secret info)
          |                                                     |
          | ----> submit_clue(room_code, token, clue) --------> | (Validates & saves)
          | <---- clue_submitted(player_name, clue) ----------- | (Broadcasts clue)
          |                                                     |
          | ----> cast_vote(room_code, token, target_id) ------> | (Saves vote)
          | <---- vote_results(tally, eliminated_player) ----- | (Broadcasts result)
          | <---- game_over(winning_role, word, player_roles) -- | (Broadcasts endgame)
```

---

## 🔄 4. Complete Game Loop & Flowchart

```
                 +--------------------------+
                 |    1. Login & Hub        |
                 | (Enter Name -> Get Token)|
                 +-------------+------------+
                               |
                               v
                 +--------------------------+
                 |    2. Lobby Room         |
                 | (Share Code, Add AI,     |
                 |  Customize Settings)     |
                 +-------------+------------+
                               |
                   [Creator clicks Start]
                               v
                 +--------------------------+
                 |    3. Role Reveal        |
                 |  (Direct secret_word /   |
                 |   role delivery)         |
                 +-------------+------------+
                               |
                     [All Players Ready]
                               v
              +--->+--------------------------+
              |    |    4. Clue Phase         |
              |    | (Submit 1 word clue;     |
              |    |  Bots generate clues)    |
              |    +-------------+------------+
              |                  |
              |            [All Clues In]
              |                  v
              |    +--------------------------+
              |    |    5. Vote Phase         |
              |    | (Cast vote on suspicious |
              |    |  players; LR bot votes)  |
              |    +-------------+------------+
              |                  |
              |          [All Votes Tallied]
              |                  v
              |    +--------------------------+
              |    |    6. Evaluation         |
              |    | (Eliminate, check ending |
              |    |  conditions)             |
              |    +-------------+------------+
              |                  |
              |         [Game Continues?]
              +-------- Yes      No
                                 |
                                 v
                 +--------------------------+
                 |    7. Game Over          |
                 | (Reveal roles, scores,   |
                 |  secret word)            |
                 +--------------------------+
```

---

## 🤖 5. Machine Learning Integration

The game integrates two machine learning models (trained via `scikit-learn` and stored as `.pkl` files using `joblib`).

### Model 1: KNN Word Suggestion (Word Guessing Bot)
*   **Purpose:** Allows the AI Imposter to attempt to guess the secret word using clues provided by Crewmates.
*   **Features:** Words are mapped to feature vectors: `[category_id, subcategory_id, word_length, commonality]`.
*   **Logic:**
    1.  Collects all clues submitted by players.
    2.  Translates clues into estimated features.
    3.  Runs a K-Nearest Neighbors query against the word database.
    4.  Selects the nearest neighbor word.
    5.  Falls back to category-level default word if confidence bounds fail.

### Model 2: Logistic Regression (Voting Bot)
*   **Purpose:** Decides who the bot should vote for during the voting phase.
*   **Features:**
    *   `votes_received`: Number of votes targeted at this player so far.
    *   `round_number`: Current round.
    *   `players_remaining`: Count of remaining active players.
    *   `bot_role`: Binary indicator of the bot's own role.
    *   `clue_similarity_score`: Vector distance metric of player's clue compared to known/suspected secret word vectors.
*   **Logic:** Run a probability prediction (`predict_proba`) for each player's likelihood of being the Imposter. Cast the bot's vote for the player with the highest probability.

---

## 🔒 6. Security & Defense Matrix

Adhering to strict OWASP standards, the application implements robust server-side security.

| Risk Category | Specific Threat | Mitigation Strategy | Implementation Details |
| :--- | :--- | :--- | :--- |
| **Injection** | SQL Injection via player names or game clues. | ORM enforcement and strict parameterization. | SQLAlchemy handles all DB transactions; no raw SQL string concatenation. |
| **Access Control** | IDOR (Insecure Direct Object Reference) trying to access `/room/OTHER_CODE`. | Token-to-session association validation. | Sockets and routes validate `session['player_token']` against the requested `room_code` database mapping. |
| **XSS** | Malicious script execution via public chat boxes or player names. | Output auto-escaping and input constraints. | Jinja auto-escaping templates; strict length and regex limits on player names and clues. |
| **Configuration Leak**| Leaking database credentials, secret keys, or debug stack traces. | Environment variables and global exception handling. | `SECRET_KEY` pulled from runtime env. Global error handlers (403, 404, 500) return user-friendly, traceback-free HTML pages. |
| **Input Abuse** | Resource exhaustion or buffer overflows in text inputs. | Strict input sanitation and schema validators. | Form controls use server-side length limits and validation functions (e.g. `validate_player_name()`). |
