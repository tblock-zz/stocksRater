"""CLI für stocksRater.

Beispiele (siehe docs/examples.md für konkrete Ticker):
  python -m src.cli --ticker <symbol>
  python -m src.cli --tickers <sym1>,<sym2>,<sym3>
  python -m src.cli --ticker <symbol> --json
  python -m src.cli --tickers <sym1>,<sym2> --backtest --report reports/bt.json
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

# Pfad-Setup, damit `python -m src.cli` funktioniert
_HERE = Path(__file__).resolve().parent
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from stockscheck.rater import rate_one, rate_many, format_rating, format_table, format_compact, format_compact_table
from stockscheck.backtest import backtest_symbol, backtest_portfolio


def parse_args():
    p = argparse.ArgumentParser(description="Aktien-Rating (Technical + Fundamental)")
    p.add_argument("--ticker", type=str, help="Einzelnes Symbol")
    p.add_argument("--tickers", type=str, help="Komma-getrennte Liste")
    p.add_argument("--json", action="store_true", help="JSON-Output")
    p.add_argument("--backtest", action="store_true", help="Backtest laufen lassen")
    p.add_argument("--report", type=str, help="Report-Datei für Backtest (JSON)")
    p.add_argument("--period", type=str, default="5y", help="Datenperiode (default 5y)")
    p.add_argument("--compact", action="store_true", help="Telegram-Format (1 Zeile pro Rating)")
    return p.parse_args()


def get_symbols(args) -> list:
    syms = []
    if args.ticker:
        syms.append(args.ticker.strip())
    if args.tickers:
        syms.extend([s.strip() for s in args.tickers.split(",") if s.strip()])
    return syms


def main():
    args = parse_args()
    symbols = get_symbols(args)
    if not symbols:
        print("Bitte --ticker oder --tickers angeben", file=sys.stderr)
        sys.exit(1)

    if args.backtest:
        # Backtest-Modus
        if len(symbols) == 1:
            r = backtest_symbol(symbols[0], period=args.period)
            out = {"single": r.to_dict()}
        else:
            out = backtest_portfolio(symbols, period=args.period)
        if args.json or args.report:
            text = json.dumps(out, indent=2, default=str)
            if args.report:
                Path(args.report).parent.mkdir(parents=True, exist_ok=True)
                Path(args.report).write_text(text)
                print(f"Report written: {args.report}")
            else:
                print(text)
        else:
            # Konsolen-Output
            if "summary" in out:
                s = out["summary"]
                print(f"Symbole getestet: {s['symbols_tested']}")
                print(f"Ø Buy & Hold: {s['avg_buy_hold_return_pct']:+.1f}%")
                print(f"Ø Strategie : {s['avg_strategy_return_pct']:+.1f}%")
                print(f"Win-Rate    : {s['avg_win_rate_pct']:.0f}%")
                print(f"Trades total: {s['total_trades']}")
                print(f"Strategie schlägt B&H: {'JA' if s['strategy_outperforms'] else 'NEIN'}")
                print()
                for r in out["results"]:
                    print(f"  {r['symbol']}: B&H {r['buy_hold_return_pct']:+.1f}%, Strat {r['strategy_return_pct']:+.1f}%, "
                          f"{r['num_trades']} Trades, WR {r['win_rate_pct']:.0f}%")
            else:
                r = out["single"]
                print(f"=== {r['symbol']} ===")
                print(f"B&H       : {r['buy_hold_return_pct']:+.1f}%")
                print(f"Strategie : {r['strategy_return_pct']:+.1f}%")
                print(f"Trades    : {r['num_trades']}")
                print(f"Win-Rate  : {r['win_rate_pct']:.0f}%")
                print(f"Avg Win   : {r['avg_win_pct']:+.1f}%")
                print(f"Avg Loss  : {r['avg_loss_pct']:+.1f}%")
                print(f"Max DD    : {r['max_drawdown_pct']:.1f}%")
        return

    # Rating-Modus
    if len(symbols) == 1:
        rating = rate_one(symbols[0], period=args.period)
        if args.json:
            print(json.dumps(rating.to_dict(), indent=2, default=str))
        elif args.compact:
            print(format_compact(rating))
        else:
            print(format_rating(rating))
    else:
        ratings = rate_many(symbols, period=args.period)
        if args.json:
            print(json.dumps([r.to_dict() for r in ratings], indent=2, default=str))
        elif args.compact:
            print(format_compact_table(ratings))
        else:
            print(format_table(ratings))


if __name__ == "__main__":
    main()