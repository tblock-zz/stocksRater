#!/usr/bin/env bash
# stocksRater-Launcher: richtet .venv bei Bedarf ein und fuehrt das Rating aus.
# Aufruf: ./rate.sh <TICKER> [TICKER2 ...] [--json] [--backtest] [...]
# Alle Parameter werden 1:1 an python -m src.cli durchgereicht.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

PY=".venv/bin/python"

# --- .venv pruefen/anlegen ---
if [ ! -x "$PY" ]; then
  echo "==> .venv nicht gefunden — erstelle Environment und installiere Dependencies..."
  if ! command -v python3 >/dev/null 2>&1; then
    echo "FEHLER: python3 nicht gefunden. Bitte Python 3.10+ installieren." >&2
    exit 1
  fi
  python3 -m venv .venv
  .venv/bin/pip install --quiet --upgrade pip
  .venv/bin/pip install --quiet -r requirements.txt
  echo "==> Setup abgeschlossen."
fi

# --- Argumente sortieren: nackte Ticker -> --tickers, Rest 1:1 durchreichen ---
TICKERS=""
ARGS=()
for a in "$@"; do
  case "$a" in
    -*) ARGS+=("$a") ;;
    *)  TICKERS="${TICKERS:+$TICKERS,}$a" ;;
  esac
done

if [ -z "$TICKERS" ]; then
  echo "Usage: $0 TICKER [TICKER ...] [--json] [--backtest] [--report FILE] [--compact]"
  echo "Beispiele: $0 AAPL"
  echo "           $0 AAPL MSFT NVDA"
  echo "           $0 AAPL --json"
  echo "           $0 AAPL MSFT --backtest"
  exit 1
fi

exec "$PY" -m src.cli --tickers "$TICKERS" "${ARGS[@]}"
