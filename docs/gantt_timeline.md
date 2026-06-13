# Imposter Game — Development Timeline (Gantt Chart Reference)

## Overview
| Milestone | Phase | Duration | Dates |
|-----------|-------|----------|-------|
| M1 | Project Foundation | 1 week | Week 1 |
| M2 | Core Game Engine | 2 weeks | Weeks 2–3 |
| M3 | ML Bot Integration | 1.5 weeks | Weeks 3–4 |
| M4 | Multiplayer & Real-Time | 2 weeks | Weeks 5–6 |
| M5 | Multi-Device Mode | 1.5 weeks | Weeks 7–8 |
| M6 | ML Analytics & Smart Assignment | 2 weeks | Weeks 8–9 |
| M7 | UI/UX & Accessibility | 1 week | Week 10 |
| M8 | Security, Testing, Polish | 1.5 weeks | Weeks 10–11 |
| M9 | Deployment & Documentation | 0.5 weeks | Week 12 |

---

## Detailed Task Breakdown

### M1 — Project Foundation (Week 1)

| Task | Description | Dependencies |
|------|-------------|--------------|
| 1.1 | Flask application scaffold (factory pattern, blueprints) | — |
| 1.2 | SQLite database setup via SQLAlchemy ORM | 1.1 |
| 1.3 | Configuration management (`.env`, `Config` class) | 1.1 |
| 1.4 | Static file structure (CSS, templates) | 1.1 |
| 1.5 | Basic route skeleton (lobby, game, settings) | 1.2 |
| 1.6 | Jinja2 base template with Tailwind CDN | 1.4 |

### M2 — Core Game Engine (Weeks 2–3)

| Task | Description | Dependencies |
|------|-------------|--------------|
| 2.1 | Database models: `Game`, `Player`, `Round`, `Vote` | 1.2 |
| 2.2 | Role assignment (imposter/crewmate/jester) | 2.1 |
| 2.3 | Secret word selection from JSON dictionary (510 words, 10 categories) | 1.3 |
| 2.4 | Game phase state machine (lobby → reveal → clue → vote → result) | 2.1 |
| 2.5 | Clue submission and storage per round | 2.4 |
| 2.6 | Vote tallying with tiebreaker (random pick) | 2.5 |
| 2.7 | Elimination logic (`was_voted_out` flag) | 2.6 |
| 2.8 | Win condition checks (imposter majority, all imposters elim'd, jester voted out) | 2.7 |
| 2.9 | Round progression loop | 2.8 |
| 2.10 | Pass-and-play HTTP routes (setup form, game view, clue/vote POST) | 1.5 |
| 2.11 | Role reveal page with role-specific UI | 2.10 |

### M3 — ML Bot Integration (Weeks 3–4)

| Task | Description | Dependencies |
|------|-------------|--------------|
| 3.1 | Word dictionary feature engineering (category_id, subcategory_id, word_length, commonality) | 2.3 |
| 3.2 | KNN word-guessing bot (`ml/word_bot.py`) | 3.1 |
| 3.3 | Feature vector extraction from clue text | 3.2 |
| 3.4 | KNN model training + persistence (`knn_model.pkl`) | 3.2–3.3 |
| 3.5 | Synthetic vote data generator (`ml/generate_vote_data.py`) | — |
| 3.6 | Logistic Regression voting bot (`ml/vote_bot.py`) | 3.5 |
| 3.7 | Clue similarity heuristic for vote features | 3.6 |
| 3.8 | LR model training + persistence (`lr_model.pkl`) | 3.6–3.7 |
| 3.9 | AI bot player toggle in setup | 2.10 |
| 3.10 | Bot clue generation integration | 3.4 |
| 3.11 | Bot vote casting in game flow | 3.8 |
| 3.12 | Bot guess display on result page | 3.4 |
| 3.13 | `/bot/guess` API endpoint | 3.4 |

### M4 — Multiplayer & Real-Time (Weeks 5–6)

| Task | Description | Dependencies |
|------|-------------|--------------|
| 4.1 | Flask-SocketIO integration | 1.1 |
| 4.2 | SocketIO event namespace design | 4.1 |
| 4.3 | Room creation and join/leave events | 4.2 |
| 4.4 | Real-time clue submission event | 4.3 |
| 4.5 | Real-time vote casting event | 4.3 |
| 4.6 | Auto phase transition when all players submitted | 4.4–4.5 |
| 4.7 | Player connection/disconnection tracking | 4.3 |
| 4.8 | Lobby system with player list UI | 4.3 |
| 4.9 | Chat/message system (basic) | 4.2 |
| 4.10 | SocketIO polling-only fallback for PythonAnywhere | 4.1 |
| 4.11 | Lazy-load sklearn module to speed cold start | 3.4, 3.8 |
| 4.12 | 28 integration tests for lobby flow | 4.1–4.11 |

### M5 — Multi-Device Mode (Weeks 7–8)

| Task | Description | Dependencies |
|------|-------------|--------------|
| 5.1 | Multi-device setup form (host enters player names) | 2.10 |
| 5.2 | Room code generation (6-char alphanumeric) | 4.3 |
| 5.3 | Host token generation (`secrets.token_urlsafe`) | 4.1 |
| 5.4 | QR code generation for join URL | 5.2 |
| 5.5 | Host dashboard page with QR display | 5.4 |
| 5.6 | Join page with player name selection buttons | 5.2 |
| 5.7 | Player token claim flow (first-click-get-token) | 5.6 |
| 5.8 | Player game page (role reveal, clue, vote per device) | 5.7 |
| 5.9 | Host-only advance phase event | 5.5 |
| 5.10 | Game stats page for manual winner entry | 5.9 |
| 5.11 | Play-again (repeat) flow for multi-device | 5.10 |

### M6 — ML Analytics & Smart Assignment (Weeks 8–9)

| Task | Description | Dependencies |
|------|-------------|--------------|
| 6.1 | `GameEvent` model for audit logging | 2.1 |
| 6.2 | Per-player historical stats aggregation | 6.1 |
| 6.3 | `imposter_score()` weighted formula | 6.2 |
| 6.4 | `start_player_score()` weighted formula | 6.2 |
| 6.5 | `_weighted_pick()` — weighted random selection | 6.3–6.4 |
| 6.6 | `balanced_role_assign()` — smart role distribution | 6.5 |
| 6.7 | `pick_starting_player()` — adaptive starter | 6.5 |
| 6.8 | Gaussian Naive Bayes winner prediction model | 6.1 |
| 6.9 | Category difficulty analysis (win rates per category) | 6.1 |
| 6.10 | Balanced category pick (weighted toward fair categories) | 6.9 |
| 6.11 | Per-word win rate tracking | 6.1 |
| 6.12 | Balanced word selection | 6.11 |
| 6.13 | Smart role toggle in settings | 5.11 |
| 6.14 | Smart role integration in game creation | 6.6, 6.13 |
| 6.15 | AI insights panel with random tips | 6.8 |
| 6.16 | Example game seeding (8 synthetic games on fresh DB) | 6.1 |
| 6.17 | `/api/ml/history` REST API endpoint | 6.1–6.12 |
| 6.18 | Stats page with prediction, career stats, event log | 5.10, 6.15 |

### M7 — UI/UX & Accessibility (Week 10)

| Task | Description | Dependencies |
|------|-------------|--------------|
| 7.1 | Home page redesign (3-mode layout) | 4.1 |
| 7.2 | Expandable rules/roles section | 7.1 |
| 7.3 | Button styling (rectangular, rounded, sizing) | 7.1 |
| 7.4 | Dark mode toggle + persistence | 7.1 |
| 7.5 | High contrast mode (WCAG-friendly) | 7.4 |
| 7.6 | Adjustable font size (14/16/18/20px) | 7.4 |
| 7.7 | Mobile-responsive design (breakpoints) | 7.1 |
| 7.8 | Touch-friendly minimum targets (44px) | 7.7 |
| 7.9 | Role-specific colour scheme | 7.1 |
| 7.10 | Category difficulty labels in dropdowns | 6.9, 7.1 |
| 7.11 | Dynamic JS tooltip for difficulty info | 7.10 |

### M8 — Security, Testing & Polish (Weeks 10–11)

| Task | Description | Dependencies |
|------|-------------|--------------|
| 8.1 | Input sanitisation (`strip_html`, block SQL patterns) | — |
| 8.2 | Player name validation (regex, length) | 8.1 |
| 8.3 | Clue validation (XSS prevention, SQL injection blocklist) | 8.1 |
| 8.4 | Chat message validation | 8.1 |
| 8.5 | SocketIO rate limiting (10 events/sec sliding window) | 4.1 |
| 8.6 | Session-based game access guard (`game_session_required`) | 8.5 |
| 8.7 | Cryptographic host + player tokens | 5.3 |
| 8.8 | Numeric parameter validation (`validate_positive_int`) | 8.1 |
| 8.9 | Custom error pages (403, 404, 500) | 8.6 |
| 8.10 | Test fixtures (in-memory SQLite, app factory) | — |
| 8.11 | Test suite: HTTP routes | 8.10 |
| 8.12 | Test suite: Game logic edge cases | 8.10 |
| 8.13 | Test suite: Multi-device flow | 8.10 |
| 8.14 | Test suite: SocketIO events | 8.10 |
| 8.15 | Test suite: Security validations | 8.10 |

### M9 — Deployment & Documentation (Week 12)

| Task | Description | Dependencies |
|------|-------------|--------------|
| 9.1 | PythonAnywhere WSGI configuration (`wsgi.py`) | 1.1 |
| 9.2 | Environment variable documentation (`.env.example`) | 1.3 |
| 9.3 | README with full feature table, architecture, setup guide | All |
| 9.4 | Mermaid context diagram (DFD Level 0) | 9.3 |
| 9.5 | Project structure map | 9.3 |
| 9.6 | ML component documentation | 9.3 |
| 9.7 | Cleanup stale artifacts + planning docs | All |

---

## Gantt Chart Mapping

```
Week:     1   2   3   4   5   6   7   8   9   10  11  12
M1     ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
M2     ░░░░████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
M3     ░░░░░░░░████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░
M4     ░░░░░░░░░░░░░░░░░░████████████████░░░░░░░░░░░░░░░░░
M5     ░░░░░░░░░░░░░░░░░░░░░░░░░░████████████░░░░░░░░░░░░░
M6     ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░████████████████░░░
M7     ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░████████░░░░░
M8     ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██████████░
M9     ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░█████
```

## Dependency Graph (Critical Path)

```
1.1 → 1.2 → 2.1 → 2.4 → 2.5 → 2.6 → 2.7 → 2.8 → 2.9
  ↓                                         
  ├→ 3.1 → 3.2 → 3.4
  ├→ 3.5 → 3.6 → 3.8
  ├→ 4.1 → 4.2 → 4.3 → 4.4 → 4.6
  │                          ↓
  └→ 5.1 → 5.2 → 5.4 → 5.5
        5.2 → 5.6 → 5.7 → 5.8
                          5.9 → 5.10 → 5.11
                                         ↓
                         6.1 → 6.2 → ... → 6.18
```

## Resource Estimates

| Resource | Estimate |
|----------|----------|
| Total development time | ~12 weeks |
| Core Python/Flask | ~3000 lines |
| ML models | 3 (GaussianNB, KNN, Logistic Regression) |
| Database tables | 7 |
| Templates | 12 |
| Tests | 28 (HTTP + SocketIO + Logic) |
| Word dictionary | 510 words, 10 categories |
