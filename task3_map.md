# Imposter Game — Task 3 To-Do Map

## 1. Flask Conversion (Do First)
- [ ] Replace `app.py` HTTP server with a proper Flask app
- [ ] Create `templates/` folder and move game HTML into Jinja templates
- [ ] Split into `base.html` + page templates
- [ ] Set up `static/` folder for CSS/JS
- [ ] Migrate `word-dictionary.js` to a Python dict/JSON with fields: `word, category, subcategory, word_length, commonality`
- [ ] Test game is fully playable in Flask locally

---

## 2. Database
- [ ] Install SQLAlchemy
- [ ] Create `models.py` with these tables:
  - `games` — game_id, date, num_players, winning_role, secret_word, category
  - `players` — player_id, game_id, name, role, was_voted_out
  - `rounds` — round_id, game_id, round_number, clue_given, player_id
  - `votes` — vote_id, game_id, round_id, voter_id, target_id
  - `words` — word_id, word, category_id, subcategory_id, word_length, commonality
- [ ] Hook up DB to Flask in `app.py`
- [ ] Test all tables create correctly on startup

---

## 3. Flask Routes
- [ ] `GET /` — home/lobby
- [ ] `POST /game/new` — create game, assign roles, pick secret word
- [ ] `GET /game/<id>` — current game state
- [ ] `POST /game/<id>/clue` — submit a clue, save to DB
- [ ] `POST /game/<id>/vote` — submit vote, trigger bot vote
- [ ] `POST /bot/guess` — bot uses KNN to guess the word
- [ ] `GET /game/<id>/result` — show outcome, save game to DB

---

## 4. KNN Model (Word Suggestion)
- [ ] Expand word dictionary to 100+ words with category/subcategory/commonality
- [ ] Encode words as feature vectors `[category_id, subcategory_id, word_length, commonality]`
- [ ] Train `KNeighborsClassifier` from scikit-learn on the word vectors
- [ ] Save trained model as `knn_model.pkl` with joblib
- [ ] Write `bot_guess(clues)` function that loads model and returns nearest word
- [ ] Handle unknown/custom words with a category-level fallback
- [ ] Test bot guessing with a few sample clue sets

---

## 5. Logistic Regression Model (Voting)
- [ ] Generate synthetic training data (game scenarios with vote outcomes)
- [ ] Features: `votes_received, round_number, players_remaining, bot_role, clue_similarity_score`
- [ ] Train `LogisticRegression` from scikit-learn
- [ ] Save as `lr_model.pkl` with joblib
- [ ] Write `bot_vote(game_state)` function that returns player to vote for
- [ ] Wire into `POST /game/<id>/vote` route
- [ ] Test bot voting in both Crewmate and Imposter roles

---

## 6. Security
- [ ] Set `SECRET_KEY` via environment variable (never hardcoded)
- [ ] Set `DEBUG=False` in production config
- [ ] Confirm all DB queries go through SQLAlchemy ORM (no raw SQL strings)
- [ ] Add session validation to all game routes (check game_id belongs to session)
- [ ] Add server-side input validation on all POST routes
- [ ] Run **Bandit**: `bandit -r app.py models.py routes/` — fix all findings
- [ ] Run **Flake8**: `flake8 --max-line-length=100 .` — fix all warnings
- [ ] Manual DAST on live URL:
  - [ ] Try SQL injection in player name/word fields
  - [ ] Try accessing another game's URL directly
  - [ ] Submit empty/oversized forms
  - [ ] Trigger a 500 and confirm no stack trace shown to user

---

## 7. Deployment
- [ ] Push all code to GitHub
- [ ] Set up PythonAnywhere with Python 3
- [ ] Configure WSGI file
- [ ] Set environment variables on PythonAnywhere
- [ ] Confirm static files load correctly
- [ ] Do a full playthrough on the live URL
- [ ] Add live URL to README and Part A doc title page

---

## 8. Code Cleanup
- [ ] Add meaningful comments to all ML logic explaining the math
- [ ] Add comments to all security patches explaining what they fix
- [ ] PEP 8 pass with Flake8 — no remaining warnings
- [ ] Remove any dead/leftover code from the HTML prototype
- [ ] Write `README.md` with:
  - How to run locally
  - Live URL
  - Security patch summary
  - Automation/ML summary
  - AI usage acknowledgement

---

## 9. GitHub Commits (need 15+ total)
Aim for one commit per item above. Good examples:
- `Set up Flask app and replaced HTTP server`
- `Created SQLite schema — games, players, rounds, votes, words`
- `Migrated word dictionary to Python with feature vectors`
- `Implemented KNN word suggestion model`
- `Generated synthetic training data for Logistic Regression`
- `Implemented Logistic Regression voting bot`
- `Ran Bandit SAST — patched SQL injection risk in /game/new`
- `Added session validation to all game routes`
- `Deployed to PythonAnywhere — ran DAST manual tests`
- `PEP 8 cleanup with Flake8`

---

## 10. Part A Docs (marks reminder)
| Section | What | Marks |
|---|---|---|
| 1.1 | Justify KNN + Logistic Regression choices | 3 |
| 1.2 | Level 0 Context Diagram | 2 |
| 2.1 | OWASP vulnerability table (2 vulns + patches) | 3 |
| 2.2 | SAST & DAST testing plan | 2 |
| 3.1 | 15+ GitHub commits | 3 |
| 3.2 | Gantt chart (10 weeks) | 2 |
| 4.1 | Level 1/2 DFD through security + both ML models | 5 |
| 5.1 | Flowchart of bot decision logic | 3 |
| 5.2 | Database schema diagram | 2 |
| **Total** | | **25** |
