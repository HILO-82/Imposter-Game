# Imposter Game — Social Deduction with ML-Driven Automation

A web-based social deduction word game (inspired by "Undercover" / "Werewords") built with **Flask**, enhanced by **Machine Learning** for adaptive role assignment, winner prediction, and gameplay insights. Supports both single-device pass-and-play and multi-device real-time play via WebSockets.

---

## Table of Contents

- [How It Works](#how-it-works)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [ML Components](#ml-components)
- [Security](#security)
- [Setup & Running](#setup--running)
- [Testing](#testing)
- [Deployment](#deployment)

---

## How It Works

A secret word is chosen from a category (Animals, Food, Sports, etc.):

| Role | Sees the word? | Goal |
|------|---------------|------|
| **Crewmate** | Yes | Identify fellow crewmates via one-word clues; vote out imposters |
| **Imposter** | No | Blend in, mislead crewmates, avoid elimination |
| **Jester** | Partial / None | Get voted out to win |

**Per round:** players submit a one-word clue, then vote to eliminate a suspected imposter.
Game ends when all imposters are eliminated (crewmates win), imposters equal crewmates (imposters win), or a jester is voted out.

---

## Features

### Core Gameplay

| Feature | Details |
|---------|---------|
| **Single-Device (Pass-and-Play)** | All players share one device; sequential role reveal with tap-to-advance |
| **Multi-Device (Real-Time)** | Each player uses their own phone; QR code join; SocketIO live updates |
| **3 Roles** | Crewmate, Imposter, Jester (with 4 configurable info levels: nothing, category, first-letter, full word) |
| **Configurable Counts** | 2–8 players, 0–4 imposters, 0–2 jesters |
| **10 Word Categories** | 510 words across Animals, Food, Colors, Objects, Places, Nature, Technology, Sports, Movies, Music |
| **Custom Secret Word** | Option to override the random word selection |
| **Play Again** | One-click replay with same players and settings, different secret word |

### ML-Driven Automation

| Feature | Technique | What It Does |
|---------|-----------|-------------|
| **Balanced Role Assignment** | Weighted random selection from historical per-player stats | Players who were imposter recently (and got caught early) have lower probability next time; players who rarely get the role have higher probability |
| **Adaptive Starting Player** | Weighted scoring (`100 - starts×2 + start_losses×3`) | Players who have started less — or started and lost more — get priority to start |
| **Winner Prediction** | Gaussian Naive Bayes classifier | Predicts which role will win based on `[player_count, imposter_count, jester_count, category_id]`. Displays confidence % on the stats page |
| **Category Difficulty** | Historical win-rate analysis | Each category labelled "Crewmate-favored", "Imposter-favored", or "Balanced" based on past games |
| **Balanced Category Selection** | Weighted pick toward balanced categories | When Smart Role Assignment is on, categories with balanced outcomes are preferred |
| **Word Balance Tracking** | Per-word historical win rates | Words where both sides win equally are preferred when smart assignment is active |
| **AI Insights Panel** | Random tip from aggregated stats | Always visible on home page; shows personalised tips like "Imposters win 40% of 6-player games" |
| **Per-Player Career Stats** | Aggregation over all finished games | Games played, wins by role, survival rounds, first-elimination count — displayed on the stats page |
| **KNN Word-Guessing Bot** | k-Nearest Neighbors (k=5, distance-weighted) | Predicts the secret word from submitted clues using a feature vector `[category_id, subcategory_id, word_length, commonality]` — displayed on result pages |
| **Logistic Regression Voting Bot** | Logistic Regression + heuristic clue similarity | Automatically casts votes for bot players based on `[votes_received, round_number, players_remaining, bot_role, clue_similarity]` |
| **Grace Bonus (Early Elimination)** | `imposter_score += first_eliminations × 15` | Players eliminated in round 1 get a significant boost to imposter probability in future games — gives them a fairer chance |
| **Example Game Seeding** | Auto-generates 8 finished games on fresh database | Ensures ML models have data to train on immediately, no grind required |
| **REST API** | `/api/ml/history` JSON endpoint | Exports player stats, category stats, word ratings, and insights for external tooling / data science integration |

### Real-Time Multiplayer (SocketIO)

| Event | Description |
|-------|------------|
| `join_game` | Player joins a SocketIO room by room code; authenticates via token |
| `advance_phase` | Host-only: transitions from role reveal to clue phase |
| `submit_clue` | Rate-limited (*10 req/s*) one-word clue submission per player |
| `cast_vote` | Rate-limited vote with duplicate detection |
| Auto phase transition | When all alive humans have submitted clues/votes, phase advances automatically |

### UI / UX

- **Dark Mode** toggle — persists across sessions via Settings
- **High Contrast Mode** — WCAG-friendly thick borders and underlined links
- **Adjustable Font Size** — 14px / 16px / 18px / 20px options
- **Responsive Design** — mobile-first with breakpoints at 768px and 480px
- **Touch-Friendly** — 44px minimum touch targets
- **Role-Specific Colours** — red (imposter), blue (crewmate), green (jester)
- **QR Code Join** — server-generated QR image using the `qrcode[pil]` library
- **Category Difficulty Labels** — shown in dropdowns on both setup pages with dynamic JS tooltip
- **Persistent Settings** — Game defaults (imposter count, jester info, category) and appearance saved to SQLite

### Security

- **Input Sanitisation** — all player names, clues, and messages validated server-side; HTML tags stripped; SQL injection patterns blocked
- **Session Guards** — `game_session_required` decorator aborts 403 on mismatch
- **Cryptographic Tokens** — `secrets.token_urlsafe(32)` for both host and player tokens in multi-device mode
- **SocketIO Rate Limiting** — sliding window: max 10 events per second per session
- **Parameter Validation** — `validate_positive_int()` on all numeric inputs
- **Custom Error Pages** — 403, 404, 500 rendered via `error.html`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, Flask 3.0, Flask-SQLAlchemy 3.1 |
| **Real-Time** | Flask-SocketIO 5.3, python-socketio 5.9 |
| **ML / AI** | scikit-learn 1.4 (GaussianNB, KNeighborsClassifier, LogisticRegression), joblib 1.3 |
| **Database** | SQLite via SQLAlchemy 2.0 ORM |
| **Frontend** | Jinja2 templates, Tailwind CSS (CDN), Font Awesome, vanilla JS |
| **QR Codes** | qrcode[pil] |
| **Testing** | pytest 7+, Flask test client, SocketIO test client |
| **Deployment** | WSGI (PythonAnywhere-ready), environment-based config with python-dotenv |

### Database Schema (7 tables)

| Table | Purpose |
|-------|---------|
| `games` | Game session, config, status, phase, round tracking |
| `players` | Player identity, role, colour, elimination, bot flag |
| `rounds` | One-word clues per player per round |
| `votes` | Vote records per round |
| `game_events` | Event log (eliminations, role reveals, etc.) |
| `settings` | Single-row persistent config (defaults + appearance) |
| `words` | Word dictionary with category, subcategory, length, commonality |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    IMPOSTER GAME SYSTEM                       │
│                                                               │
│  ┌──────────────┐   ┌──────────────────┐   ┌──────────────┐ │
│  │ Web Routes    │──►│ Game Logic       │──►│ Database     │ │
│  │ (Flask HTTP)  │   │ (win, round,     │   │ (SQLite ORM) │ │
│  └──────┬───────┘   │  role assign)     │   └──────▲───────┘ │
│         │           └─────────▲────────┘            │       │
│         ▼                     │                      │       │
│  ┌──────────────┐   ┌────────┴────────┐   ┌─────────┴────┐ │
│  │ SocketIO      │   │ ML Assignment   │   │ ML Insights  │ │
│  │ Events        │   │ Engine          │   │ Engine       │ │
│  │ (real-time)   │   │ (weighted role, │   │ (Naive Bayes  │ │
│  └──────┬───────┘   │  starter, grace) │   │  prediction, │ │
│         │           └─────────────────┘   │  tips, stats) │ │
│         │                                  └──────────────┘ │
│  ╔═══════════════════════ SECURITY ═══════════════════════════╗ │
│  ║ Input Sanitisation │ Session Auth │ Tokens │ Rate Limit  ║ │
│  ╚═══════════════════════════════════════════════════════════╝ │
└──────────────────────────────────────────────────────────────┘
         ▲                    ▲                    ▲
         │                    │                    │
         ▼                    ▼                    ▼
    ┌──────────┐       ┌───────────┐       ┌──────────┐
    │  Player  │       │  Settings │       │ SQLite   │
    │ (Users)  │       │   Admin   │       │ Storage  │
    └──────────┘       └───────────┘       └──────────┘
```

### Data Flow (Level 0 DFD)

```mermaid
graph TD
    P["Player"]:::entity
    AD["Admin / Settings"]:::entity

    subgraph SYS["Imposter Game System"]
        direction TB
        UI["Web Routes & Templates"]
        GL["Game Logic<br/>(win check, round mgmt)"]
        MLA["ML Assignment<br/>(role, starter, grace)"]
        MLI["ML Insights<br/>(predict, tips, stats)"]

        GL -->|"win check, roles"| UI
        UI -->|"names, clues, votes"| GL
        MLA -->|"assigned roles + starter"| GL
        MLI -->|"tips, predictions, labels"| UI
    end

    DB[("SQLite Database")]:::store

    UI -->|"game state"| P
    P -->|"input"| UI
    AD -->|"smart_assign, defaults"| UI
    UI -->|"settings saved"| AD
    GL -->|"games, players, events":::flow --> DB
    DB -->|"finished games":::flow --> MLA
    DB -->|"finished games":::flow --> MLI

    S1["① Input sanitisation"]:::sec
    S2["② Session token auth"]:::sec
    S3["③ Param validation"]:::sec
    UI -.- S1 & S2 & S3

    classDef entity fill:#e1f5fe,stroke:#0288d1,stroke-width:2px
    classDef system fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef store fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    classDef sec fill:#fce4ec,stroke:#c62828,stroke-width:1px
    classDef flow fill:none,stroke:#666
```

---

## ML Components

### Module Map

| Module | File | Key Functions |
|--------|------|--------------|
| **Assignment Engine** | `ml/assignment.py` | `balanced_role_assign()`, `pick_starting_player()`, `imposter_score()`, `start_player_score()`, `_weighted_pick()` |
| **Insights Engine** | `ml/insights.py` | `predict_winner()` (GaussianNB), `compute_insights()`, `random_tip()`, `get_category_difficulty()`, `balanced_word()`, `balanced_category_pick()`, `seed_example_games()` |
| **Word Bot** | `ml/word_bot.py` | `bot_guess()` (k-NN, k=5), `clues_to_features()`, `train_and_save()` |
| **Vote Bot** | `ml/vote_bot.py` | `bot_vote()` (Logistic Regression), `_clue_similarity()` |
| **Synthetic Data** | `ml/generate_vote_data.py` | `generate_synthetic_vote_data(2000)` — 5-feature training set with noise |
| **Training** | `ml/train_models.py` | Trains and persists KNN + LR models to `.pkl` files |

### Smart Role Assignment Algorithm

1. Query `GameEvent` + `Player` tables for all finished games
2. Compute per-player stats: games played, wins by role, survival rounds, first eliminations
3. Score each player for each role using weighted formulas:
   - **Imposter score** = `crewmate_win_rate×20 + survival_avg×3 + games_as_imposter×5 + first_eliminations×15`
   - **Player higher values** = more likely to get the role (weighted random, not deterministic)
4. Pick `imposter_count` imposters via `_weighted_pick()`, then `jester_count` jesters from remaining
5. Remaining players become crewmates

Key design decision: **weighted random ≠ deterministic ranking**. Lower-scored players still have a non-zero chance, keeping games unpredictable and fun.

### Winner Prediction Model (Naive Bayes)

- **Features**: `[num_players, imposter_count, jester_count, category_id]`
- **Target**: `winning_role` (crewmate / imposter / jester)
- **Training data**: all finished games from the database + 8 pre-seeded example games
- **Output**: predicted role + confidence percentage (probability of the predicted class)

---

## Security

| Checkpoint | Implementation | Location |
|-----------|---------------|----------|
| Input sanitisation | `strip_html()`, block SQL patterns, enforce length limits | `security.py:3-35` |
| Session auth | `game_session_required` decorator, abort 403 on mismatch | `security.py:37-49` |
| Cryptographic tokens | `secrets.token_urlsafe(32)` for host + player tokens | `routes/game.py` |
| SocketIO rate limit | Sliding window: 10 events/sec/session | `security.py:15-28` |
| Numeric validation | `validate_positive_int(min, max)` on all IDs and counts | `security.py:29-34` |
| Error pages | Custom 403 / 404 / 500 templates | `app.py` |

---

## Setup & Running

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd Imposter-Game

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate  # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env   # Windows
# cp .env.example .env   # Mac/Linux
# Edit .env to taste (SECRET_KEY, DATABASE_URL, etc.)

# 5. Initialise database (creates tables + seeds words + seeds 8 example games)
flask shell
>>> from app import create_app
>>> from extensions import db
>>> app = create_app()
>>> with app.app_context():
...     db.create_all()
...     from words import seed_words_table
...     from models import Word
...     seed_words_table(db.session, Word)
...     from ml.insights import seed_example_games
...     seed_example_games()
...     db.session.commit()
>>> exit()

# 6. Train ML models (optional — models will train on first use)
python -c "from ml.train_models import main; main()"

# 7. Run the app
python app.py
# → http://localhost:5001
```

### Important: Fresh Database

If the schema changes, delete the old `imposter.db` and `__pycache__` directories to avoid `no such column` errors:

```bash
Remove-Item imposter.db -Force; Get-ChildItem -Recurse -Directory __pycache__ | Remove-Item -Recurse -Force
```

---

## Testing

```bash
pytest -v
```

Tests cover:

| Category | Tests |
|----------|-------|
| **HTTP Routes** | Home renders, settings loads, setup form validations, game creation, clue submission, voting flow |
| **Game Logic** | Role assignment distribution, edge cases (too few players, no jesters, all imposters) |
| **Multi-Device** | Setup page, game creation, QR join flow |
| **SocketIO** | Join real-time room, empty clue rejection, duplicate clue rejection, XSS clue rejection |
| **Security** | Input validation edge cases, session guards |

Test configuration uses an **in-memory SQLite database** (`sqlite:///:memory:`) so no files are written during tests.

---

## Deployment (PythonAnywhere)

```bash
# On PythonAnywhere:
git clone https://github.com/HILO-82/Imposter-Game
cd Imposter-Game

# Set up virtualenv and install
pip install --user flask flask-sqlalchemy flask-socketio scikit-learn joblib python-dotenv qrcode[pil] eventlet

# WSGI config — set project_home explicitly:
#   project_home = "/home/yourusername/Imposter-Game"
```

**Note**: when deploying, delete the old `imposter.db` and any `__pycache__` directories from the server so the new schema takes effect.

---

## Project Structure

```
├── app.py                  # Flask app factory, error handlers
├── config.py               # Environment-based configuration
├── extensions.py           # SQLAlchemy + SocketIO init
├── models.py               # 7 ORM models
├── game_logic.py           # Core game rules engine
├── security.py             # Input validation, rate limiting, guards
├── room_manager.py         # Room code generation + creation
├── socketio_events.py      # Real-time game events
├── words.py                # Word dictionary loader + helpers
├── wsgi.py                 # PythonAnywhere entry point
│
├── ml/
│   ├── __init__.py
│   ├── assignment.py       # Balanced role + starter assignment
│   ├── insights.py         # Winner prediction, tips, stats
│   ├── word_bot.py         # KNN word-guessing bot
│   ├── vote_bot.py         # Logistic Regression voting bot
│   ├── generate_vote_data.py  # Synthetic training data
│   └── train_models.py     # Model training pipeline
│
├── routes/
│   ├── __init__.py
│   ├── lobby.py            # Home page
│   ├── game.py             # All game endpoints + API
│   └── settings.py         # Settings CRUD
│
├── templates/              # 12 Jinja2 templates
├── static/css/style.css    # Custom styles
├── data/words.json         # 510 words across 10 categories
│
├── tests/
│   ├── conftest.py         # In-memory app + fixtures
│   └── test_lobby.py       # 18 tests (HTTP + SocketIO + logic)
│
├── docs/context_diagram.md # Mermaid architecture diagram
├── knn_model.pkl           # Trained KNN model (generated)
├── lr_model.pkl           # Trained LR model (generated)
└── requirements.txt
```

---

## License

Educational project — 12SE Software Engineering (Task 3).
