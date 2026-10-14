# AGENTS.md — Machine-Readable Setup Instructions for AI Agents

You (the agent) set up this project fully autonomously. Follow the steps exactly in this order. Run all commands from the repo root.

## Target State (Definition of Done)

1. `.venv/` exists with all dependencies installed
2. `pytest` runs with 70 passed, 0 failed
3. `python -m src.cli --ticker AAPL` produces a Markdown rating report
4. All four checks below have each succeeded once

## Step 1 — Dependencies

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Error handling:
- `python3` missing → install Python 3.10+ (apt/brew), then retry.
- No network → abort and inform the operator; this project needs internet
  for pip AND for the live rating calls (Yahoo Finance).

## Step 2 — Unit Tests (no network required)

```bash
.venv/bin/python -m pytest tests/ -q
```

Expected: `70 passed`. On failures: do NOT "fix" the code — check the
Python version (3.10+ required, tested with 3.14) and rule out environment
factors (PYTHONPATH, stale .venv); then inform the operator.

## Step 3 — Live Smoke Test (needs internet, ~5-10 s)

```bash
.venv/bin/python -m src.cli --ticker AAPL
```

Expected: a Markdown report starting with `# AAPL — Grade ...`.
Success check: output contains `Grade` and `Score`.
Known failure scenarios:
- `"'str' object has no attribute 'name'"` or `No price data found`
  → yfinance too old. Fix: `.venv/bin/pip install -U yfinance` (>= 1.5 required).
- Rate limit / timeout → wait 30 s, retry once; then inform the operator.
- `SyntaxWarning: 'return' in a 'finally' block` is HARMLESS (vendor code
  wart) — do not treat it as an error.

## Step 4 — Backtest Check (optional, ~1-2 min)

```bash
.venv/bin/python -m src.cli --tickers AAPL,MSFT,KO --backtest
```

Expected: comparison table of strategy vs Buy&Hold.

## Usage After Setup (recommended: launcher)

The launchers `rate.sh` (bash) and `rate.ps1` (PowerShell) check at startup
whether `.venv` exists: if missing, it is created with all dependencies; if
present, it is used directly. Afterwards they run the rating. Bare tickers
are automatically combined into `--tickers`.

```bash
./rate.sh AAPL            # bash: on-demand setup + rating
./rate.sh AAPL KO --json  # multiple tickers, JSON output
```
```powershell
.\rate.ps1 AAPL           # PowerShell (Windows): identical behavior
.\rate.ps1 AAPL KO --json
```

## Direct Usage (alternative to the launcher)

```bash
.venv/bin/python -m src.cli --ticker <SYMBOL>          # single report (Markdown)
.venv/bin/python -m src.cli --tickers A,B,C            # table, sorted by score
.venv/bin/python -m src.cli --ticker A --json          # JSON (machine-readable)
.venv/bin/python -m src.cli --tickers A,B --backtest --report reports/bt.json
./scripts/run_rating.sh AAPL MSFT                      # convenience wrapper
BACKTEST=1 ./scripts/run_rating.sh KO
```

## Reference: Scoring (details in README.md)

- Score 0–100: Technical 55 (SMA trend, RSI, MACD, Stochastic, Fib) +
  Fundamentals 45 (P/E, P/B, FairValue margin, D/E+FCF) + Bonus 8
- Grades: A ≥75 STRONG BUY | B 60–74 BUY | C 45–59 HOLD | D 30–44 AVOID | F <30 SELL
- Data source: on-the-fly Yahoo Finance, no local data store
- JSON consumers: `--json` returns an array; per ticker one object with, among
  others, `symbol`, `total_score`, `grade`, `action`, `technical_total`,
  `value_total`, `reasons` (list), `fundamentals` (object with `price`,
  `kgv_trailing`, ...).

## Rules for Agents

- Never edit files under `src/` or `tests/` to make tests "pass".
- `.venv` belongs in the repo root (it is in .gitignore, do not commit it).
- On unfixable errors: abort setup and inform the operator with the full
  error output — never report fabricated results.
