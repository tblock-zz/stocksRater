#!/usr/bin/env bash
# One-Shot Setup: installiert Dependencies und führt Smoke-Test aus.
# Aufruf: ./scripts/install.sh [TICKER]
# Setze TEST_TICKER=<symbol>, um einen anderen Ticker für den Smoke-Test zu nutzen.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
cd "$ROOT"

TEST_TICKER="${TEST_TICKER:-${1:-AAPL}}"

echo "==> Installiere Python-Dependencies (pip install -r requirements.txt)"
python3 -m pip install -r requirements.txt

echo
echo "==> Smoke-Test: pytest"
python -m pytest tests/ -v

echo
echo "==> Smoke-Test: Rating (Ticker: $TEST_TICKER, max 90s)"
if timeout 90 python -m src.cli --ticker "$TEST_TICKER" > /tmp/rating.out 2>&1; then
  echo "OK — Rating erstellt (siehe /tmp/rating.out)"
  head -10 /tmp/rating.out
else
  echo "WARNUNG: Rating fehlgeschlagen — möglicherweise yfinance-Rate-Limit oder kein Internet."
  echo "Ausgabe:"
  cat /tmp/rating.out
  exit 1
fi

echo
echo "==> Setup abgeschlossen. Nutze:"
echo "    python -m src.cli --ticker <symbol>"
echo "    python -m src.cli --tickers AAPL,MSFT,NVDA"
echo "    python -m src.cli --ticker AAPL --backtest"
echo "    ./scripts/run_rating.sh AAPL MSFT"
