# SAST & DAST — Security Verification Plan

## Static Application Security Testing (SAST)

SAST analyses source code without executing it, catching vulnerabilities early in the development lifecycle.

### 1. Flake8 (Linting + Security Checks)

**Purpose:** Enforce code style, detect syntax errors, and flag dangerous patterns.

**Current config** (`.flake8`):
```
[flake8]
max-line-length = 100
exclude = .git,__pycache__,venv,.venv,imposter-game.html
ignore = E501,W503
```

**How it will be used:**
- Run on every push to check for basic code quality issues
- The `max-line-length=100` prevents overly complex one-liners that hide logic errors
- Plugins can be added to extend security coverage:

| Plugin | What it catches |
|--------|----------------|
| `flake8-bandit` | Wraps Bandit checks into Flake8 output |
| `flake8-bugbear` | Dangerous defaults, mutable arguments, `+=` on lists |
| `flake8-assertive` | Catches `assert` statements used in non-test code (can be stripped by `-O`) |

**Command:**
```bash
flake8 .
```

### 2. Bandit (Python-Specific SAST)

**Purpose:** Identify common security issues: hardcoded passwords, SQL injection vectors, unsafe `eval()`, insecure `yaml.load()`, etc.

**How it will be used:**
- Scan the entire codebase before each release
- Configured via `pyproject.toml` or `.bandit` file
- Skips test files and virtual environments

**Configuration** (add to `pyproject.toml`):
```toml
[tool.bandit]
exclude_dirs = ["tests", "venv", ".venv", "__pycache__"]
skips = ["B101"]  # allow assert in test code
```

**Relevant checks for this project:**

| Bandit ID | What it flags | Where it applies in this project |
|-----------|---------------|----------------------------------|
| B102 | `exec()` used | N/A — not used |
| B103 | `set_bad_file_permissions` | N/A |
| B105 | Hardcoded password strings | Ensures `SECRET_KEY` isn't hardcoded in production |
| B106 | Hardcoded password (config) | Checks `config.py` for dev-only keys |
| B107 | Hardcoded password (other) | General password scan |
| B108 | Insecure temp file | N/A |
| B110 | `try` / `except` / `pass` | Catches bare except blocks that swallow errors |
| B112 | `try` / `continue` / `except` / `pass` | Same pattern detection |
| B201 | Flask app run with `debug=True` | Catches `app.run(debug=True)` committed to prod |
| B301 | `pickle` / `cPickle` deserialisation | N/A — using `joblib` (safe for trusted data) |
| B302 | `marshal` deserialisation | N/A |
| B303 | `md5` / `sha1` used for security | N/A — using `secrets` module |
| B304 | CIPHERS | N/A |
| B305 | `ssl._create_default_https_context` | N/A |
| B306 | `mktemp` | N/A |
| B310 | `urllib.urlopen()` — no timeout | N/A |
| B311 | `random` used for security purposes | Checks that game logic uses `random` not `secrets` (intentional — game shuffling uses `random`) |
| B320 | `input()` in Python 3 | N/A |
| B321 | F-strings in `logging` calls | Flags lazy-formatting issues |
| B322 | `tarfile` extraction | N/A |
| B323 | `yaml.load()` without `Loader` | N/A |
| B324 | `ssl.wrap_socket` | N/A |
| B325 | `tempfile.mktemp` | N/A |
| B401 | `import subprocess` | Detects if subprocess is used unsafely |
| B402 | `import xml.etree` | N/A |
| B403 | `import pickle` | Flags pickle usage |
| B404 | `import subprocess` (with unsafe shell) | Catches `shell=True` |
| B405 | `start_process_with_a_shell` | Catches `shell=True` in subprocess |
| B406 | `start_process_with_no_shell` | N/A |
| B407 | `start_process_with_partial_path` | N/A |
| B408 | `import xml.dom.minidom` | N/A |
| B409 | `import xml.sax` | N/A |
| B410 | `import lxml` | N/A |
| B411 | `import xml.etree.cElementTree` | N/A |
| B412 | `import copyreg` | N/A |
| B413 | `import pickle` / `cPickle` | Flags pickle usage |
| B501 | `request_with_no_cert_validation` | N/A |
| B502 | `ssl_with_bad_version` | N/A |
| B503 | `ssl_with_bad_defaults` | N/A |
| B504 | `ssl_with_no_version` | N/A |
| B505 | `weak_cryptographic_key` | N/A |
| B506 | `yaml_load` | N/A |
| B507 | `ssh_no_host_key_verification` | N/A |
| B601 | `paramiko_calls` | N/A |
| B602 | `ssl_wrap_socket` | N/A |
| B603 | `subprocess_without_shell_equals_true` | Ensures subprocess calls are safe |
| B604 | `any_other_function_with_shell_equals_true` | Detects `shell=True` anywhere |
| B605 | `start_process_with_a_shell` | Duplicate |
| B606 | `start_process_with_no_shell` | Duplicate |
| B607 | `start_process_with_partial_path` | Duplicate |
| B608 | `hardcoded_sql_expressions` | Flags string-concatenated SQL (caught by `security.py` validation) |
| B609 | `linux_commands_wildcard_injection` | N/A |
| B610 | `django_extra_requires_extra` | N/A |
| B611 | `django_rawsql_used` | N/A |
| B701 | `jinja2_autoescape_false` | N/A — Jinja2 auto-escapes by default in Flask |
| B702 | `use_of_mark_safe` | N/A |
| B703 | `django_mark_safe` | N/A |

**Command:**
```bash
bandit -r . -c pyproject.toml
```

### 3. Automated CI Pipeline (Future)

In a CI environment (GitHub Actions), both tools would run automatically:

```yaml
# .github/workflows/security.yml
name: Security Scan
on: [push, pull_request]
jobs:
  sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install flake8 flake8-bandit bandit
      - run: flake8 .
      - run: bandit -r . -c pyproject.toml
```

---

## Dynamic Application Security Testing (DAST)

DAST tests the running application by simulating real-world attacks. It catches vulnerabilities SAST might miss — especially in configuration, runtime behaviour, and input/output handling.

### 1. Input Injection Testing

Test that the application rejects or sanitises malicious input at every entry point.

| Entry Point | Test Vector | Expected Behaviour |
|-------------|-------------|--------------------|
| Player name form | `<script>alert('xss')</script>` | Stripped or rejected (via `strip_html()`) |
| Player name form | `Robert'; DROP TABLE players;--` | SQL not executed (ORM parameterises queries) |
| Player name form | `" OR 1=1 --` | Returns empty result (ORM prevents injection) |
| Player name form | `a` × 1000 | Rejected (`MAX_NAME_LENGTH=50`) |
| Clue field | `<img src=x onerror=alert(1)>` | Rejected via `validate_clue()` |
| Clue field | `' UNION SELECT * FROM games--` | Rejected via blocklist in `validate_clue()` |
| Clue field | `a` × 10000 | Rejected (`MAX_CLUE_LENGTH=100`) |
| Chat message | `<script>...</script>` | Stripped via `strip_html()` or rejected |

### 2. Session / Token Testing

| Test | Method | Expected Behaviour |
|------|--------|--------------------|
| Access game without session | Navigate to `/game/1` directly | 403 Forbidden (`game_session_required`) |
| Tamper session `game_id` | Modify Flask session cookie | 403 on mismatch |
| Access multi-device host dashboard without host_token | Visit `/multi-device/dashboard/1` directly | Redirected to home |
| Claim another player's name | POST `/multi-device/join/<code>` with another player's ID | No-auth — any name can be claimed (current design) |
| Replay old token | Use expired player_token from previous game | Player not found → redirected to join page |
| URL manipulation | Change `token` parameter in play URL | Player not found → redirected to join page |

### 3. Rate Limit Testing

| Test | Method | Expected Behaviour |
|------|--------|--------------------|
| Clue submission flood | Send 20+ clue submissions in 1 second via SocketIO | Requests after 10th are silently dropped (`rate_limit()` returns False) |
| Vote flood | Same pattern for vote events | Same — sliding window rejects excess |

### 4. Game Logic Abuse

| Test | Method | Expected Behaviour |
|------|--------|--------------------|
| Vote while eliminated | POST vote for eliminated player | Rejected (`voter.was_voted_out`) |
| Vote for eliminated player | POST vote with eliminated target_id | Rejected (`target.was_voted_out`) |
| Submit clue when eliminated | POST clue for eliminated player | Rejected (`player.was_voted_out`) |
| Submit clue in wrong phase | POST clue during vote phase | Rejected (`game.phase != "clue"`) |
| Double vote | POST two votes in same round | Second vote rejected (duplicate detection) |
| Submit clue for another player | POST clue with different player_id in body | Allowed in single-device pass-and-play (by design) |
| Submit clue for another player (multi-device) | SocketIO submit_clue with wrong token | Token doesn't match player → no-op |

### 5. Resource / Information Leakage

| Test | Method | Expected Behaviour |
|------|--------|--------------------|
| 404 page on invalid game | Visit `/game/99999` | Custom 404 page, no stack trace |
| 500 on malformed input | POST invalid data types | Custom 500 page, no debug info |
| Error detail exposure | Trigger an exception with `DEBUG=False` | Generic error page (`security.py` enforced) |
| Secret word leakage | Inspect HTML source on player's page | Imposter page does not render `game.secret_word` |

### 6. Dependency Vulnerability Scan

| Tool | Command | Purpose |
|------|---------|---------|
| `pip-audit` | `pip-audit` | Scans `requirements.txt` for known CVEs in Flask, SQLAlchemy, scikit-learn, etc. |
| `safety` | `safety check -r requirements.txt` | Alternative CVE database lookup |

---

## SAST + DAST Combined Schedule

| Phase | Frequency | Tools | Scope |
|-------|-----------|-------|-------|
| Per commit | Every push | Flake8 | Code style, syntax errors |
| Pre-release | Before each release | Bandit, Flake8 | Full SAST scan |
| Pre-release | Before each release | Input injection, session tests | Manual DAST via checklist |
| Monthly | Once per month | `pip-audit` | Dependency CVE scan |
| Major release | Per major version | Full manual pen test | All DAST checklists above |

---

## Example SAST Run

```bash
$ bandit -r routes/game.py

[main]  INFO  profile include tests: None
[main]  INFO  exclude tests: None
[main]  INFO  found issues:
No issues identified.
```

```bash
$ flake8 .
# No output = clean
```

## Example DAST Walkthrough (Manual)

1. Open two browser tabs: one as host dashboard, one as join page
2. Join as a player, observe `player_token` in URL
3. Tamper the token → redirected to join page (expected)
4. Submit `<script>alert(1)</script>` as a clue → check if script executes (should not)
5. Rapid-fire clue submissions via browser console → verify rate limit kicks in
6. Try to vote twice in the same round → second vote silently ignored
7. Open `/game/1` without session → 403 page rendered
