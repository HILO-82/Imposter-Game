# Part A Documentation Outline (25 marks)

Use this outline when writing your formal Part A report. Diagrams can be created in draw.io, Lucidchart, or similar.

## 1.1 ML justification (3 marks)

**KNN for word guessing**

- Words are encoded as numeric feature vectors (category, subcategory, length, commonality).
- k-NN finds the dictionary word closest to clue-derived features without assuming linear boundaries.
- Suitable for small labelled dataset (510 words) and interpretable “nearest word” behaviour.

**Logistic Regression for voting**

- Binary outcome: “should this player be eliminated this round?”
- Linear model on interpretable features (suspicion from votes, round, crew size, role, clue fit).
- Fast inference at vote time; coefficients explain bot strategy for report.

## 1.2 Level 0 Context Diagram (2 marks)

Entities: Player (browser), Flask App, SQLite DB, KNN Model file, LR Model file, PythonAnywhere host.

## 2.1 OWASP table (3 marks)

| Vulnerability | Example | Patch |
|---------------|---------|-------|
| Injection | `'; DROP TABLE--` in name | ORM + input validation in `security.py` |
| Broken access control | `/game/5` with session for game 3 | `require_game_session()` → 403 |

## 2.2 SAST & DAST plan (2 marks)

- SAST: Bandit + Flake8 in CI or pre-deploy (commands in README).
- DAST: manual checklist on live URL (README section).

## 3.1 GitHub commits (3 marks)

Aim for 15+ focused commits (examples in `task3_map.md`).

## 3.2 Gantt chart (2 marks)

10-week plan: Flask → DB → routes → KNN → LR → security → deploy → docs.

## 4.1 Level 1/2 DFD (5 marks)

Show data flow: setup → `POST /game/new` → clues → votes → bot guess/vote → result → DB tables.

Include security validation step and both ML model calls.

## 5.1 Bot decision flowchart (3 marks)

```
Clues collected → KNN bot_guess → display on result
Vote submitted → build feature vector per player → LR predict_proba → pick max → cast bot vote
```

## 5.2 Database schema diagram (2 marks)

ER diagram for games, players, rounds, votes, words with foreign keys as in `models.py`.
