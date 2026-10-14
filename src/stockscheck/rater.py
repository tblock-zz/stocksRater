"""Orchestrator: lädt Daten, baut Technical + Fundamental, scored."""
from __future__ import annotations
import pandas as pd
from typing import List, Optional

try:
    from .stockscheck_bridge import loadTickerData
    from .indicators import build_technical
    from .fundamentals import fetch_fundamentals, FundamentalResult
    from scorer import build_rating, StockRating
except ImportError:
    from .stockscheck_bridge import loadTickerData
    from .indicators import build_technical
    from .fundamentals import fetch_fundamentals, FundamentalResult
    from .scorer import build_rating, StockRating


def rate_one(symbol: str, period: str = "5y", interval: str = "1d") -> StockRating:
    """Bewertet eine einzelne Aktie komplett (Tech + Fund + Score)."""
    df = loadTickerData(symbol, interval)
    tech = build_technical(symbol, df)
    fund = fetch_fundamentals(symbol)
    return build_rating(tech, fund)


def rate_many(symbols: List[str], period: str = "5y", interval: str = "1d") -> List[StockRating]:
    """Bewertet mehrere Aktien. Fehler pro Symbol werden ignoriert (geloggt)."""
    ratings = []
    for sym in symbols:
        try:
            r = rate_one(sym, period, interval)
            ratings.append(r)
        except Exception as e:
            print(f"[WARN] {sym}: {e}")
    return ratings


def format_rating(r: StockRating) -> str:
    """Formatierte Markdown-Tabelle für eine Bewertung."""
    t = r.technical
    f = r.fundamental
    lines = []
    lines.append(f"# {r.symbol} — Grade **{r.grade}** — {r.action}")
    lines.append(f"**Score:** {r.total_score:.1f} / 100  |  **Preis:** {f.price:.2f}  |  **Datum:** {pd.Timestamp(t.last_date).strftime('%Y-%m-%d')}")
    lines.append("")
    lines.append("## Technical (max 55)")
    lines.append(f"| Indikator | Wert | Signal | Pkt |")
    lines.append(f"|---|---|---|---|")
    lines.append(f"| Trend (SMA50 vs SMA200) | {t.sma50:.2f} vs {t.sma200:.2f} ({t.sma50_vs_sma200_pct:+.1f}%) | {t.trend} | {r.trend_pts:.0f}/15 |")
    lines.append(f"| RSI (14) | {t.rsi:.1f} | {t.rsi_signal} | {r.rsi_pts:.0f}/10 |")
    lines.append(f"| MACD | {t.macd:.2f} / Sig {t.macd_signal:.2f} | {t.macd_trend} | {r.macd_pts:.0f}/10 |")
    lines.append(f"| Stochastik | {t.stoch_slow:.1f} | {t.stoch_signal} | {r.stoch_pts:.0f}/10 |")
    # Fibonacci-Info
    fib = t.fib
    fib_str = f"{fib.nearest_level*100:.1f}% ({fib.distance_pct:+.1f}% zum nächsten Level)"
    lines.append(f"| Fibonacci | {fib_str} | {fib.trend} | {r.fib_pts:.0f}/10 |")
    lines.append(f"| **Total Technical** | | | **{r.technical_total:.0f}/55** |")
    lines.append("")
    lines.append("## Fundamentals (max 45 + Bonus)")
    lines.append(f"| Metrik | Wert | Signal | Pkt |")
    lines.append(f"|---|---|---|---|")
    kgv_str = f"{f.kgv_trailing:.1f}" if f.kgv_trailing else "n/a"
    kbv_str = f"{f.kbv:.2f}" if f.kbv else "n/a"
    fv_str = f"{f.fair_value_margin_pct:+.1f}%" if f.fair_value_margin_pct is not None else "n/a"
    de_str = f"{f.debt_to_equity:.2f}" if f.debt_to_equity is not None else "n/a"
    fcf_str = f"{f.fcf_yield_pct:.1f}%" if f.fcf_yield_pct is not None else "n/a"
    lines.append(f"| KGV (trailing) | {kgv_str} | | {r.kgv_pts:.0f}/10 |")
    lines.append(f"| KBV | {kbv_str} | | {r.kbv_pts:.0f}/10 |")
    lines.append(f"| FairValue-Marge | {fv_str} | | {r.fv_pts:.0f}/15 |")
    lines.append(f"| Debt/Equity + FCF | D/E={de_str}, FCF-Y={fcf_str} | | {r.health_pts:.0f}/10 |")
    lines.append(f"| **Total Value** | | | **{r.value_total:.0f}/45** |")
    div_str = f"{f.dividend_yield_pct:.1f}%" if f.dividend_yield_pct is not None else "n/a"
    lines.append(f"| Dividenden-Bonus | {div_str} | | {r.div_bonus:.0f}/3 |")
    lines.append(f"| Analysten-Bonus | {f.recommendation or 'n/a'} | | {r.analyst_bonus:.0f}/3 |")
    lines.append("")
    lines.append("## Begründung")
    if r.reasons:
        for reason in r.reasons:
            lines.append(f"- {reason}")
    else:
        lines.append("- Keine besonders starken Signale")
    return "\n".join(lines)


def format_table(ratings: List[StockRating]) -> str:
    """Markdown-Tabelle für mehrere Bewertungen, sortiert nach Score."""
    ratings_sorted = sorted(ratings, key=lambda r: r.total_score, reverse=True)
    lines = []
    lines.append(f"# Aktien-Rating ({len(ratings_sorted)} Stück)")
    lines.append("")
    lines.append("| Symbol | Grade | Score | Preis | RSI | Trend | KGV | KBV | FV-Marge |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for r in ratings_sorted:
        t = r.technical
        f = r.fundamental
        kgv = f"{f.kgv_trailing:.1f}" if f.kgv_trailing else "n/a"
        kbv = f"{f.kbv:.2f}" if f.kbv else "n/a"
        fv = f"{f.fair_value_margin_pct:+.0f}%" if f.fair_value_margin_pct is not None else "n/a"
        price = f"{f.price:.2f}" if f.price else "n/a"
        lines.append(
            f"| {r.symbol} | **{r.grade}** | {r.total_score:.0f} | {price} | "
            f"{t.rsi:.0f} | {t.trend} | {kgv} | {kbv} | {fv} |"
        )
    return "\n".join(lines)


def format_compact(r: StockRating) -> str:
    """Einzeilige Telegram-freundliche Zusammenfassung (1 Zeile)."""
    f = r.fundamental
    price = f"{f.price:.2f}" if f.price else "n/a"
    return f"**{r.symbol}** {r.grade} {r.total_score:.0f}/100 ({r.action}) · €{price} · {r.technical.rsi:.0f} RSI · {r.technical.trend}"


def format_compact_table(ratings: List[StockRating]) -> str:
    """Mehrere Ratings in kompakter Telegram-Form, sortiert nach Score."""
    ratings_sorted = sorted(ratings, key=lambda r: r.total_score, reverse=True)
    return "\n".join(format_compact(r) for r in ratings_sorted)