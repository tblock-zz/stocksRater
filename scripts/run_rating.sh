#!/usr/bin/env bash
# Convenience wrapper für gängige Rating-Kommandos.
# Aufruf: ./scripts/run_rating.sh TICKER [TICKER ...]
# Beispiel: ./scripts/run_rating.sh AAPL MSFT NVDA
#           BACKTEST=1 ./scripts/run_rating.sh KO

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
cd "$ROOT"

if [ $# -eq 0 ]; then
  echo "Usage: $0 TICKER [TICKER ...]"
  echo "Beispiel: $0 AAPL MSFT NVDA"
  echo "Mit Backtest: BACKTEST=1 $0 KO"
  exit 1
fi

TICKERS=$(IFS=, ; echo "$*")

if [ "${BACKTEST:-0}" = "1" ]; then
  exec python -m src.cli --tickers "$TICKERS" --backtest
else
  exec python -m src.cli --tickers "$TICKERS"
fi
