# Examples & Reference Runs

Konkrete Beispiel-Ticker, Ausgaben und Backtest-Befunde. Diese Datei gehört zum **Projekt**, nicht zum Skill — sie ist optionale Lese-Empfehlung für den ersten Eindruck.

## Schnellstart

```bash
cd ~/repos/stocksRater
pip install -r requirements.txt

# Einzelne Aktie (volle Markdown-Tabelle)
python -m src.cli --ticker AAPL

# Watchlist (Telegram-kompakt, 1 Zeile pro Aktie)
python -m src.cli --tickers AAPL,MSFT,NVDA,KO,JNJ --compact

# Backtest (5 Jahre, Walk-Forward alle 30 Tage)
python -m src.cli --ticker KO --backtest --period 5y

# Backtest-Report als JSON
python -m src.cli --ticker KO --backtest --report reports/ko_bt.json
```

## Beispiel-Output: AAPL (Compact)

```
**AAPL** D 44/100 (AVOID) · €308.91 · 35 RSI · up
```

## Beispiel-Output: Watchlist (5 Aktien, Compact, sortiert nach Score)

```
**JNJ** B 63/100 (BUY) · €256.35 · 49 RSI · up
**KO** C 55/100 (HOLD) · €87.59 · 64 RSI · up
**AAPL** D 44/100 (AVOID) · €308.91 · 35 RSI · up
**NVDA** D 41/100 (AVOID) · €200.75 · 48 RSI · up
**MSFT** D 35/100 (AVOID) · €464.72 · 81 RSI · down
```

## Beispiel-Backtest: KO 5y

```
=== KO ===
B&H       : +78.5%
Strategie : +59.5%
Trades    : 3
Win-Rate  : 67%
Avg Win   : +26.6%
Avg Loss  : -0.1%
Max DD    : 0.1%
```

→ Strategie holt 76% des Buy&Hold-Returns bei deutlich niedrigerem Drawdown (siehe `references/backtest-caveats.md` für Methodik).

## Empirische Befunde (Aug 2026)

Welche Aktie-Typen liefern valide Backtest-Resultate, welche nicht — und warum:

### Value-Aktien (KGV ≤ 25, stabiles Bewertungsprofil)
- **Beispiele:** KO, JNJ, Banken, Versorger, REITs
- **Backtest liefert valide Resultate.** KO 5y: Strategie +59.5% vs. B&H +78.5%, 3 Trades, 67% Win-Rate, max DD 0.1%.
- **Warum:** Fundamentaldaten sind über die Zeit relativ stabil — der Look-Ahead-Bias fällt wenig ins Gewicht.

### Quality-Growth-Aktien (KGV > 30, multiple Expansion)
- **Beispiele:** AAPL, NVDA, MSFT
- **Backtest liefert 0 Trades** — die Strategie triggert nie, weil das aktuelle KGV/KBV (~30–50) auf 2022 angewendet wird und den historischen Score nie ≥ 60 bringt.
- **Bedeutung:** Die Strategie ist real nicht schlecht — die Daten sind es. Für belastbare Aussagen → v2 mit historischen Fundamentals via `quarterly_income_stmt`.

### Substanz-Aktien mit zyklischem Geschäft
- **Beispiele:** Airlines, Autohersteller, Chemie
- **Backtest-Ergebnis hängt stark vom Bewertungs-Zeitpunkt ab.** Ein hoher KGV in einer Rezession sieht heute vielleicht moderat aus, war aber damals branchenüblich. Ergebnis meist unzuverlässig.

## yfinance-Feld-Inkonsistenzen (für eigene Erweiterungen)

| Feld | yfinance liefert | Code rechnet | Korrekt? |
|---|---|---|---|
| `dividendYield` | Prozent (0.35 = 0.35%) | direkt übernommen | ✅ |
| `payoutRatio` | Bruch (0.12 = 12%) | × 100 | ✅ |
| `grossMargins` | Bruch (0.4 = 40%) | × 100 | ✅ |
| `operatingMargins` | Bruch (0.3 = 30%) | × 100 | ✅ |
| `revenueGrowth` | Bruch (0.05 = 5%) | × 100 | ✅ |
| `earningsGrowth` | Bruch (0.10 = 10%) | × 100 | ✅ |
| `debtToEquity` | Prozent (150 = 150%) | ÷ 100 | ✅ |

**AAPL-Beispiel:** `dividendYield = 0.35` (real 0.35%) wurde vor dem Fix versehentlich mit × 100 zu 35% — und löste einen ungerechtfertigten Dividenden-Bonus aus. Siehe `src/fundamentals.py:151`.

## Pitfall #9 in `SKILL.md`

Vor dem Hinzufügen eines neuen yfinance-Felds zu `fundamentals.py`: einmal alle Werte ausgeben lassen, um zu prüfen, ob sie als Prozent oder Bruch kommen. Beispiel-Code:

```python
ticker = yf.Ticker("AAPL")
for k in ["dividendYield", "payoutRatio", "grossMargins", "debtToEquity"]:
    print(f"{k:25s} = {ticker.info.get(k)}")
```
