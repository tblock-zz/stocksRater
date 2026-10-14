# stocksRater

Stock rating: technical (RSI, MACD, Stochastic, Fibonacci, SMA50/200, Bollinger)
+ fundamental (P/E, P/B, FairValue via Graham/DCF/PEG, Debt/Equity, FCF, dividends,
analyst rating) combined into a weighted score of 0-100 with grades A-F.

The package is **self-contained** — the core modules (loader, indicators,
financialData) live under `src/vendor/` (origin: the stocksCheck project) and
are wired in via `src/stockscheck/stockscheck_bridge.py`. No external project
paths required.

## For AI Agents

**If you are an AI agent:** Read [AGENTS.md](AGENTS.md) first — it contains a
machine-readable setup guide with exact commands, expected results, and error
handling. Follow it in that order.

## Installation

Easiest path: clone the repo and run `./rate.sh AAPL` — the launcher sets up
`.venv` and all dependencies automatically (see Usage below).

Manual:

```bash
git clone <repo-url> && cd stocksRater
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./scripts/install.sh AAPL   # smoke test including a real rating call
```

**Important:** use yfinance >= 1.5. Old versions (0.2.37) break against
Yahoo's API ("'str' object has no attribute 'name'").

## Usage

**Recommended: launcher** — automatically creates `.venv` on first use if
missing, reuses it afterwards, and runs the rating:

```bash
./rate.sh AAPL                      # bash: on-demand setup + rating
./rate.sh AAPL MSFT NVDA            # multiple tickers, sorted by score
./rate.sh AAPL --json               # JSON output
./rate.sh AAPL MSFT --backtest      # backtest
```
```powershell
.\rate.ps1 AAPL                     # PowerShell (Windows): identical behavior
.\rate.ps1 AAPL KO --json
```

**Direct (alternative, after manual setup):**

```bash
.venv/bin/python -m src.cli --ticker AAPL                     # single stock (Markdown report)
.venv/bin/python -m src.cli --tickers AAPL,MSFT,NVDA          # multiple, sorted by score
.venv/bin/python -m src.cli --ticker AAPL --json              # JSON output
.venv/bin/python -m src.cli --tickers AAPL,MSFT --backtest --report reports/bt.json
./scripts/run_rating.sh AAPL MSFT                             # convenience wrapper (no venv autodetect)
BACKTEST=1 ./scripts/run_rating.sh KO
```

## Scoring Model (100 points)

### Technical (55)
- Trend SMA50 vs SMA200 (15): >+5%=15, Golden Cross=12, Death Cross=0-5
- RSI 14 (10): <25=10 ... >70=0
- MACD 12/26/9 (10): rising+bullish=10, falling=1-3
- Stochastic 16/3/3 (10): <15=10, >80=0
- Fibonacci retracement (10): Goldilocks (38.2-61.8%)=10, new highs=3

### Fundamentals (45)
- Trailing P/E (10): <15=10 ... >35=0
- P/B (10): <1.5=10 ... >10=0
- FairValue margin (15): mean of Graham+DCF+PEG+Intrinsic vs price
- Debt/Equity + FCF yield (10)

### Bonus (up to 8)
- Dividend yield (3), analyst rating (3), momentum/misc (2)

### Grades
A >= 75 STRONG BUY | B 60-74 BUY | C 45-59 HOLD | D 30-44 AVOID | F < 30 SELL

## Backtest

Walk-forward (look-ahead-free via `df.loc[:date]`). Strategy: buy at score >= 60,
sell at score < 45 or after 365 days, rebalancing every 30 days.

**Limitations:** fundamental data is current (not historical per quarter) → the
backtest is approximate; in a pure bull market Buy & Hold usually beats the
strategy — its value lies in drawdown protection.

## Architecture

| File | Purpose |
|---|---|
| `src/stockscheck/stockscheck_bridge.py` | Loads vendor modules (sys.path to src/vendor) |
| `src/stockscheck/fibonacci.py` | Swing high/low + retracements |
| `src/stockscheck/indicators.py` | TechnicalResult + scoring (trend/rsi/macd/stoch/fib) |
| `src/stockscheck/fundamentals.py` | FairValue, P/E, P/B, health |
| `src/stockscheck/scorer.py` | Weighted score + grades A-F |
| `src/stockscheck/rater.py` | Orchestrator + formatting |
| `src/stockscheck/backtest.py` | Walk-forward + Buy&Hold benchmark |
| `src/cli.py` | argparse entry point (`python -m src.cli`) |
| `rate.sh` / `rate.ps1` | Launchers: venv autodetect + setup + rating |
| `src/vendor/` | stocksCheck core modules (loader, indicators, config, globals, financialData) |

Bot-detection protection: yfinance session via `curl_cffi` with Chrome impersonation.

## Tests

```bash
.venv/bin/python -m pytest tests/ -v   # 70 tests, all deterministic (no network calls)
```

## Data Source

All price and fundamental data comes on-the-fly from Yahoo Finance (yfinance).
There is no local data store; backtest reports land (optionally) under `reports/`.
