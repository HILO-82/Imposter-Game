# Imposter Game (Task 3)

Flask-based social deduction game with SQLite persistence, KNN word-guessing bot, and Logistic Regression voting bot.

## Live URL

Deploy to PythonAnywhere and set your URL here:

`https://YOUR_USERNAME.pythonanywhere.com`

## Run locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m ml.train_models   # creates knn_model.pkl and lr_model.pkl
export SECRET_KEY="your-local-secret"
python app.py
```

Open http://127.0.0.1:5000

## Game flow

1. **Lobby** — configure players, secret word, roles (`/`, `/settings`)
2. **Role reveal** — pass-and-play private role assignment
3. **Start Game** — persists to DB, adds AI imposter bot (`POST /game/new`)
4. **Rounds** — each player submits a clue (`POST /game/<id>/clue`), then vote (`POST /game/<id>/vote`)
5. **Bots** — KNN guesses word (`POST /bot/guess`); LR bot votes after human vote
6. **Result** — winner saved on `games.winning_role` (`GET /game/<id>/result`)

## API routes

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Home / lobby |
| POST | `/game/new` | Create game in DB |
| GET | `/game/<id>` | Play screen (clues / votes) |
| POST | `/game/<id>/clue` | Submit clue |
| POST | `/game/<id>/vote` | Submit vote + trigger LR bot |
| POST | `/bot/guess` | KNN word guess from clues JSON |
| GET | `/game/<id>/result` | Final outcome |

## Database schema

- `games` — game_id, date, num_players, winning_role, secret_word, category, status, round_number, phase
- `players` — player_id, game_id, name, role, was_voted_out, is_bot
- `rounds` — round_id, game_id, round_number, clue_given, player_id
- `votes` — vote_id, game_id, round_id, voter_id, target_id
- `words` — word_id, word, category_id, subcategory_id, word_length, commonality

## ML models

- **KNN** (`ml/word_bot.py`, `knn_model.pkl`) — feature vector `[category_id, subcategory_id, word_length, commonality]`; clues mapped to estimated features then nearest-neighbor word returned.
- **Logistic Regression** (`ml/vote_bot.py`, `lr_model.pkl`) — trained on synthetic scenarios; features: votes received, round number, players remaining, bot role, clue similarity.

## Security summary

| Risk | Mitigation |
|------|------------|
| SQL injection | SQLAlchemy ORM only; no raw SQL strings |
| Session hijack / IDOR | `session['game_id']` validated on all `/game/<id>` routes |
| XSS in forms | Jinja auto-escaping; clue/name length limits and pattern checks |
| Weak secret / debug leak | `SECRET_KEY` from env; custom 500 handler hides stack traces |
| Input abuse | `validate_player_name`, `validate_clue`, integer bounds on IDs |

### SAST

```bash
bandit -r app.py models.py game_logic.py security.py words.py config.py extensions.py routes/ ml/ wsgi.py
flake8 --max-line-length=100 app.py models.py game_logic.py security.py words.py config.py extensions.py routes/ ml/ wsgi.py
```

### DAST (manual, on live URL)

- [ ] SQL injection strings in player name / clue fields
- [ ] Access `/game/OTHER_ID` without matching session → expect 403
- [ ] Submit empty clue / oversized name (>50 chars)
- [ ] Trigger error path → confirm no Python traceback in browser

## PythonAnywhere deployment

1. Upload project to `/home/USERNAME/imposter`
2. Create virtualenv and `pip install -r requirements.txt`
3. Set WSGI file to import from `wsgi.py` (see `wsgi.py`)
4. Set env vars: `SECRET_KEY`, `FLASK_DEBUG=0`, `DATABASE_URL=sqlite:////home/USERNAME/imposter/imposter.db`
5. Map static files: `/static/` → `/home/USERNAME/imposter/static/`
6. Reload web app and run full playthrough

## AI usage acknowledgement

AI tools were used to assist with Flask migration, SQLAlchemy schema design, ML pipeline structure, and documentation. All code was reviewed and integrated into this repository.

## Part A documentation

See [PART_A_DOCS.md](PART_A_DOCS.md) for coursework diagrams and justification outlines.
