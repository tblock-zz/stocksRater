# stocksRater

Aktien-Bewertung: technisch (RSI, MACD, Stochastik, Fibonacci, SMA50/200, Bollinger)
+ fundamental (KGV, KBV, FairValue via Graham/DCF/PEG, Debt/Equity, FCF, Dividende,
Analysten-Rating) auf gewichteten Score 0-100 mit Grade A-F.

Das Paket ist **autark** - die Kernmodule (loader, indicators, financialData) liegen
unter `src/vendor/` (Herkunft: stocksCheck-Projekt) und werden ueber
`src/stockscheck/stockscheck_bridge.py` eingebunden. Keine externen Projektpfade noetig.

## ⚠️ Haftungsausschluss

**Das ist KEINE Anlageberatung.** Dieses Projekt ist eine technische Studie und
wird ausschließlich zu Bildungs- und Informationszwecken bereitgestellt. Nichts,
was dieses Tool erzeugt, stellt Anlageberatung, eine Empfehlung oder ein Angebot
zum Kauf bzw. Verkauf von Wertpapieren dar.

- Die Autor(inn)en übernehmen keine Garantie für Richtigkeit, Vollständigkeit
  oder Eignung für einen bestimmten Zweck.
- Märkte bergen ein erhebliches Verlustrisiko. Vergangene Kursentwicklungen
  und Backtests sind keine Garantie für zukünftige Ergebnisse — der eingebaute
  Backtest ist bewusst stark vereinfacht.
- **Jeder, der diesen Code oder dessen Ausgaben nutzt, handelt allein auf
  eigene Verantwortung und eigenes Risiko.** Immer eigene Recherche betreiben
  und vor Anlageentscheidungen einen zugelassenen Finanzberater konsultieren.

## For AI Agents

**If you are an AI agent:** Read [AGENTS.md](AGENTS.md) first — it contains a
machine-readable setup guide with exact commands, expected results, and error
handling. Follow it in that order.

## Installation

Am einfachsten: Repo klonen und `./rate.sh AAPL` aufrufen — der Launcher richtet
`.venv` und alle Dependencies automatisch ein (siehe Nutzung unten).

Manuell:

```bash
git clone <repo-url> && cd stocksRater
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./scripts/install.sh AAPL   # Smoke-Test inkl. echtem Rating-Call
```

**Wichtig:** yfinance >= 1.5 verwenden. Alte Versionen (0.2.37) brechen mit
Yahoos API ("'str' object has no attribute 'name'").

## Nutzung

**Empfohlen: Launcher** — richtet `.venv` bei Bedarf automatisch ein (beim ersten
Aufruf), nutzt es danach direkt und fuehrt das Rating aus:

```bash
./rate.sh AAPL                      # bash: Setup bei Bedarf + Rating
./rate.sh AAPL MSFT NVDA            # mehrere Ticker, sortiert nach Score
./rate.sh AAPL --json               # JSON-Output
./rate.sh AAPL MSFT --backtest      # Backtest
```
```powershell
.\rate.ps1 AAPL                     # PowerShell (Windows): identisches Verhalten
.\rate.ps1 AAPL KO --json
```

**Direkt (alternativ, nach manuellem Setup):**

```bash
.venv/bin/python -m src.cli --ticker AAPL                     # Einzelaktie (Markdown-Report)
.venv/bin/python -m src.cli --tickers AAPL,MSFT,NVDA          # mehrere, sortiert nach Score
.venv/bin/python -m src.cli --ticker AAPL --json              # JSON-Output
.venv/bin/python -m src.cli --tickers AAPL,MSFT --backtest --report reports/bt.json
./scripts/run_rating.sh AAPL MSFT                             # Convenience-Wrapper (ohne venv-Autodetect)
BACKTEST=1 ./scripts/run_rating.sh KO
```

## Scoring-Modell (100 Punkte)

### Technical (55)
- Trend SMA50 vs SMA200 (15): >+5%=15, Golden Cross=12, Death Cross=0-5
- RSI 14 (10): <25=10 ... >70=0
- MACD 12/26/9 (10): steigend+bullisch=10, fallend=1-3
- Stochastik 16/3/3 (10): <15=10, >80=0
- Fibonacci-Retracement (10): Goldilocks (38.2-61.8%)=10, neue Hochs=3

### Fundamentals (45)
- KGV trailing (10): <15=10 ... >35=0
- KBV (10): <1.5=10 ... >10=0
- FairValue-Marge (15): Mittelwert aus Graham+DCF+PEG+Intrinsic vs Preis
- Debt/Equity + FCF-Yield (10)

### Bonus (bis 8)
- Dividendenrendite (3), Analysten-Rating (3), Momentum/sonstige (2)

### Grade
A >= 75 STRONG BUY | B 60-74 BUY | C 45-59 HOLD | D 30-44 AVOID | F < 30 SELL

## Backtest

Walk-Forward (Look-Ahead-frei via `df.loc[:date]`). Strategie: Buy bei Score >= 60,
Sell bei Score < 45 oder nach 365 Tagen, Rebalancing alle 30 Tage.

**Limitationen:** Fundamentaldaten sind aktuell (nicht historisch pro Quartal) -> der
Backtest ist approximativ; in einem reinen Bullenmarkt schlaegt Buy & Hold die Strategie
meist - der Wert liegt im Drawdown-Schutz.

## Architektur

| Datei | Zweck |
|---|---|
| `src/stockscheck/stockscheck_bridge.py` | Laedt Vendor-Module (sys.path auf src/vendor) |
| `src/stockscheck/fibonacci.py` | Swing-High/Low + Retracements |
| `src/stockscheck/indicators.py` | TechnicalResult + Scorer (trend/rsi/macd/stoch/fib) |
| `src/stockscheck/fundamentals.py` | FairValue, KGV, KBV, Health |
| `src/stockscheck/scorer.py` | Gewichteter Score + Grade A-F |
| `src/stockscheck/rater.py` | Orchestrator + Formatierung |
| `src/stockscheck/backtest.py` | Walk-Forward + Buy&Hold-Benchmark |
| `src/cli.py` | argparse-Einstiegspunkt (`python -m src.cli`) |
| `rate.sh` / `rate.ps1` | Launcher: venv-Autodetect + Setup + Rating |
| `src/vendor/` | stocksCheck-Kernmodule (loader, indicators, config, globals, financialData) |

Bot-Detection-Schutz: yfinance-Session via `curl_cffi` mit Chrome-Impersonation.

## Tests

```bash
.venv/bin/python -m pytest tests/ -v   # 70 Tests, alle deterministisch (keine Netz-Calls)
```

## Datenquelle

Alle Kurs- und Fundamentaldaten kommen on-the-fly von Yahoo Finance (yfinance).
Es gibt keinen lokalen Datenspeicher; Backtest-Reports landen (optional) unter `reports/`.
