# Imposter Game — Social Deduction with ML-Driven Automation

A web-based social deduction word game (inspired by "Undercover" / "Werewords") built with **Flask**. The game is played **in person** — players sit together, talk, bluff, and vote face-to-face. The app is used only for setup, role reveal, logging eliminations, and displaying AI insights.

---

## Table of Contents

- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [ML Components](#ml-components)
- [Security Patch & Automation Notes](#security-patch--automation-notes)
- [Testing](#testing)
- [Project Structure](#project-structure)

---

## Quick Start

```bash
# 1. Clone and enter
git clone <repo-url>
cd Imposter-Game

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (optional)
copy .env.example .env     # Windows
cp .env.example .env       # Mac/Linux

# 5. Run the app (creates DB + seeds data automatically)
python app.py
# → http://localhost:5001
```

The database is created and seeded automatically on first run. If the schema changes, delete `imposter.db` first to avoid column errors.

---

## How It Works

A secret word is chosen from a category (Animals, Food, Sports, etc.):

| Role | Sees the word? | Goal |
|------|---------------|------|
| **Crewmate** | Yes | Identify fellow crewmates via one-word clues; vote out imposters |
| **Imposter** | No | Blend in, mislead crewmates, avoid elimination |
| **Jester** | Partial / None | Get voted out to win |

### In-Person Flow (how you use the app)

1. **Set up** the game — add player names, choose counts, pick a category
2. **Role reveal** — pass the device around; each player taps to see their role
3. **Play in person** — talk, bluff, argue, vote by pointing. No computers involved.
4. **After each round** — go to the Stats page and log who was eliminated
5. **Declare a winner** — click Crewmates / Imposters / Jester on the Stats page
6. **Play Again** — one click re-creates the game with the same settings

The app tracks every game's history, so the ML models get smarter over time.

---

## Features

### Core Gameplay

| Feature | Details |
|---------|---------|
| **Single-Device (Pass-and-Play)** | All players share one device; sequential role reveal with tap-to-advance |
| **Multi-Device (QR Code Join)** | Each player sees their own role on their phone; host dashboard shows QR code |
| **3 Roles** | Crewmate, Imposter, Jester (with 4 configurable info levels: nothing, category, first-letter, full word) |
| **Configurable Counts** | 2–8 players, 0–4 imposters, 0–2 jesters |
| **10 Word Categories** | 510 words across Animals, Food, Colors, Objects, Places, Nature, Technology, Sports, Movies, Music |
| **Custom Secret Word** | Option to override the random word selection |
| **Play Again** | One-click replay with same players and settings, different secret word |
| **Stats Page** | Record eliminations, view event log, declare winner — all after the in-person game finishes |

### UI / UX

- **Dark Mode** toggle — persists across sessions via Settings
- **High Contrast Mode** — WCAG-friendly thick borders and underlined links
- **Adjustable Font Size** — 14px / 16px / 18px / 20px options
- **Responsive Design** — mobile-first with breakpoints at 768px and 480px
- **QR Code Join** — server-generated QR image using the `qrcode[pil]` library
- **Persistent Settings** — Game defaults and appearance saved to SQLite

### Real-Time Multiplayer (SocketIO — for Multi-Device mode)

| Event | Description |
|-------|------------|
| `join_game` | Player joins a SocketIO room by room code; authenticates via token |
| `advance_phase` | Host-only: transitions from role reveal to clue phase |
| `submit_clue` | Rate-limited (*10 req/s*) one-word clue submission |
| `cast_vote` | Rate-limited vote with duplicate detection |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, Flask 3.0, Flask-SQLAlchemy 3.1 |
| **Real-Time** | Flask-SocketIO 5.3, python-socketio 5.9 |
| **ML / AI** | scikit-learn 1.4 (GaussianNB), joblib 1.3 |
| **Database** | SQLite via SQLAlchemy 2.0 ORM |
| **Frontend** | Jinja2 templates, Tailwind CSS (CDN), Font Awesome, vanilla JS |
| **QR Codes** | qrcode[pil] |
| **Testing** | pytest 7+, Flask test client, SocketIO test client |

### Database (5 active tables)

| Table | Purpose |
|-------|---------|
| `games` | Game session, config, status, winner, multi-device flags |
| `players` | Player identity, role, elimination status, connection state |
| `game_events` | Event log (eliminations recorded after in-person play) |
| `settings` | Single-row persistent config (defaults + appearance) |
| `words` | Word dictionary with category, subcategory, length, commonality |

*Note: `rounds` and `votes` tables exist in the code but are unused — the game is played entirely in person.*

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    IMPOSTER GAME SYSTEM               │
│                                                       │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────┐ │
│  │ Web Routes    │──►│ Game Logic   │──►│ Database │ │
│  │ (Flask HTTP)  │   │ (win check,  │   │ (SQLite) │ │
│  └──────┬───────┘   │  role assign) │   └────▲─────┘ │
│         │           └───────▲───────┘        │       │
│         ▼                   │                 │       │
│  ┌──────────────┐   ┌──────┴──────┐   ┌──────┴─────┐ │
│  │ SocketIO      │   │ Assignment  │   │ Insights   │ │
│  │ Events        │   │ (weighted   │   │ (Naive Bayes│ │
│  │ (multi-device)│   │  role pick) │   │  predict)  │ │
│  └──────┬───────┘   └─────────────┘   └────────────┘ │
│         │                                              │
│  ╔═════════════════ SECURITY ═════════════════════════╗ │
│  ║ HTML strip │ Session guard │ Tokens │ Rate Limit  ║ │
│  ╚════════════════════════════════════════════════════╝ │
└──────────────────────────────────────────────────────┘
```

Data flow:
- **Setup → Role Reveal**: app handles configuration and shows roles
- **Play Phase**: nothing happens in the code — game is played in person
- **Stats Page**: admin logs eliminations manually, declares winner
- **ML models**: read finished games from DB to assign future roles and predict winners

---

## ML Components

### Active ML Features

| Feature | Technique | What It Does |
|---------|-----------|-------------|
| **Balanced Role Assignment** | Weighted random selection from historical per-player stats | Players who were imposter recently (and got caught early) have lower probability next time; players who rarely get the role have higher probability |
| **Adaptive Starting Player** | Weighted scoring `(100 − starts×2 + start_losses×3)` | Players who have started less — or started and lost more — get priority to start |
| **Winner Prediction** | Gaussian Naive Bayes classifier | Predicts which role will win based on `[player_count, imposter_count, jester_count, category_id]`. Displays confidence % on the stats page |
| **Category Difficulty** | Historical win-rate analysis | Each category labelled "Crewmate-favored", "Imposter-favored", or "Balanced" based on past games |
| **Balanced Category Selection** | Weighted pick toward balanced categories | Categories with balanced outcomes are preferred when smart assignment is on |
| **Word Balance Tracking** | Per-word historical win rates | Words where both sides win equally are preferred |
| **AI Insights Panel** | Random tip from aggregated stats | Shows personalised tips like "Imposters win 40% of 6-player games" on the stats page |

### Legacy / Unused ML Bots

The following modules exist in the codebase but are **not part of the in-person game flow**. They were written for an earlier version with online clue/vote gameplay:

| Module | Technique | Status |
|--------|-----------|--------|
| `ml/word_bot.py` | KNN word-guessing bot | Unused — no online clue submission |
| `ml/vote_bot.py` | Logistic Regression voting bot | Unused — no online voting |
| `ml/generate_vote_data.py` | Synthetic data generator | Unused — only feeds the vote bot |
| `ml/train_models.py` | Training pipeline | Unused |

The `.pkl` model files for these bots have been removed from the repository.

---

## Security Patch & Automation Notes

### Security Patches

All patches are implemented in `security.py`:

| Patch | What it does | Line |
|-------|-------------|------|
| `strip_html()` | Removes all HTML tags from user input to prevent XSS | `security.py:32` |
| `rate_limit()` | Sliding window rate limiter — max 10 events/sec per SocketIO connection | `security.py:21` |
| `validate_message()` | Rejects messages containing HTML tags | `security.py:51` |
| `validate_clue()` | Blocks SQL injection patterns (`<script`, `drop table`, `union select`, `--`, `/*`) | `security.py:43` |
| `game_session_required` | Decorator that aborts 403 if session game_id doesn't match URL | `security.py:73` |
| `validate_player_name()` | Regex validation `^[\w\s\-'.]{1,50}$` — no HTML or special chars | `security.py:36` |
| `validate_positive_int()` | Ensures all numeric inputs are within valid ranges | `security.py:60` |

Additionally:
- **Host/player tokens** use `secrets.token_urlsafe(32)` (cryptographically random)
- **Tokens and room codes** have UNIQUE + INDEXED database constraints
- **Secret key** sourced from environment variable (falls back to dev-only default)
- **Custom error pages** for 403, 404, 500

### Automation Notes

- **Smart Role Assignment** and **Winner Prediction** run entirely inside Flask — no external API calls
- The Gaussian Naive Bayes model is rebuilt on every stats-page request, so new finished games feed back instantly
- 8 example games are seeded automatically on a fresh database so the ML model has data to train on immediately
- The `game_stats()` route handles both GET (runs the model, renders results) and POST (saves winner to DB)
- Player stats are aggregated from all finished games on every request using `get_player_stats()`

---

## Testing

```bash
pytest -v
```

**18 tests** covering:

| Category | Tests |
|----------|-------|
| **HTTP Routes** | Home renders, settings loads, setup form validations (min players), game creation, clue submission, voting flow |
| **Game Logic** | Role assignment distribution, edge cases (too few players, no jesters, all imposters) |
| **Multi-Device** | Setup page, game creation, QR join flow |
| **SocketIO** | Join real-time room, empty clue rejection, duplicate clue rejection, XSS clue rejection |
| **Security** | XSS input blocked at the SocketIO boundary |

Test configuration uses an **in-memory SQLite database** (`sqlite:///:memory:`) so no files are written during tests.

### Code Quality

```bash
pip install flake8
python -m flake8 .
```

Config in `.flake8`: `max-line-length = 100`, excludes test files and unused bot modules.

---

## Project Structure

```
├── app.py                  # Flask app factory, error handlers
├── config.py               # Environment-based configuration
├── extensions.py           # SQLAlchemy + SocketIO init
├── models.py               # 7 ORM models (5 active)
├── game_logic.py           # Core game rules engine
├── security.py             # Input validation, rate limiting, guards
├── room_manager.py         # Room code generation
├── socketio_events.py      # Real-time game events
├── words.py                # Word dictionary loader + helpers
├── wsgi.py                 # PythonAnywhere entry point
│
├── ml/
│   ├── __init__.py
│   ├── assignment.py       # Balanced role + starter assignment
│   ├── insights.py         # Winner prediction, tips, stats
│   ├── word_bot.py         # [Legacy] KNN word-guessing bot
│   ├── vote_bot.py         # [Legacy] Logistic Regression voting bot
│   ├── generate_vote_data.py  # [Legacy] Synthetic training data
│   └── train_models.py     # [Legacy] Model training pipeline
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
├── docs/                   # Planning and architecture documents
└── requirements.txt
```
