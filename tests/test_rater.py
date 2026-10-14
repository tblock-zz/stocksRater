"""Tests für rater.py: Markdown-Formatierung, Compact-Format, Edge-Cases."""
import sys
from pathlib import Path
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from stockscheck.rater import format_rating, format_table, format_compact, format_compact_table
from stockscheck.scorer import StockRating
from stockscheck.indicators import TechnicalResult
from stockscheck.fundamentals import FundamentalResult
from stockscheck.fibonacci import FibResult


def make_fib():
    return FibResult(
        swing_high=200, swing_low=100,
        swing_high_idx=pd.Timestamp("2025-01-01"),
        swing_low_idx=pd.Timestamp("2024-12-01"),
        trend="up",
        levels={0.382: 161.8, 0.5: 150.0, 0.618: 138.2},
        current_price=150.0, nearest_level=0.5, nearest_price=150.0, distance_pct=0,
    )


def make_tech(sma50=102, sma200=100, rsi=35, stoch_slow=30, fib_score=10):
    fib = make_fib()
    return TechnicalResult(
        symbol="TEST", last_price=150, last_date=pd.Timestamp("2025-01-01"),
        sma50=sma50, sma200=sma200, sma50_vs_sma200_pct=2,
        trend="up", golden_cross_recent=False, death_cross_recent=False,
        rsi=rsi, rsi_signal="buy_zone",
        macd=2, macd_signal=1, macd_diff=0.5, macd_trend="rising",
        stoch_k=stoch_slow, stoch_slow=stoch_slow, stoch_signal="buy_zone",
        bb_upper=110, bb_lower=90, bb_position=0.5, bb_signal="middle",
        fib=fib,
        sub_score_trend=12, sub_score_rsi=8, sub_score_macd=10, sub_score_stoch=7, sub_score_fib=fib_score,
    )


def make_fund(price=100, kgv=12, kbv=1.0, fair_margin=20, de=0.3, fcf_yield=6,
              div_yield=2.5, recommendation="strongBuy"):
    fair_value = price * (1 + fair_margin/100) if price and fair_margin is not None else None
    return FundamentalResult(
        symbol="TEST", price=price, kgv_trailing=kgv, kgv_forward=kgv, kbv=kbv,
        fair_value_graham=fair_value, fair_value_dcf=fair_value,
        fair_value_peg=fair_value, fair_value_intrinsic=fair_value,
        fair_value_avg=fair_value, fair_value_margin_pct=fair_margin,
        debt_to_equity=de, current_ratio=2.0, free_cashflow=1e10, fcf_yield_pct=fcf_yield,
        revenue_growth_pct=8, earnings_growth_pct=10,
        gross_margin_pct=40, operating_margin_pct=20,
        dividend_rate=div_yield, dividend_yield_pct=div_yield, payout_ratio_pct=40,
        market_cap=1e11, beta=1, fifty_day_avg=price*0.95 if price else None,
        two_hundred_day_avg=price*0.85 if price else None,
        recommendation=recommendation, target_median=price*1.2 if price else None,
        upside_pct=20,
        sub_score_value=0, sub_score_health=0, sub_score_dividend=0,
    )


def make_rating(tech=None, fund=None, **kwargs):
    if tech is None:
        tech = make_tech()
    if fund is None:
        fund = make_fund()
    defaults = dict(
        symbol="TEST", technical=tech, fundamental=fund,
        trend_pts=12, rsi_pts=8, macd_pts=10, stoch_pts=7, fib_pts=10, technical_total=47,
        kgv_pts=10, kbv_pts=10, fv_pts=12, health_pts=10, value_total=42,
        div_bonus=2, analyst_bonus=3, total_score=94, grade="A", action="STRONG BUY",
        reasons=["Starker Aufwärtstrend"],
    )
    defaults.update(kwargs)
    return StockRating(**defaults)


# ============================================================
# format_rating
# ============================================================

def test_format_rating_contains_symbol_and_grade():
    r = make_rating()
    out = format_rating(r)
    assert "TEST" in out
    assert "A" in out
    assert "STRONG BUY" in out


def test_format_rating_contains_dividend_no_bug():
    """Regression-Test für Bug 1: 'if present' toter String."""
    r = make_rating()
    out = format_rating(r)
    assert "if present" not in out, f"format_rating enthält toten String 'if present':\n{out}"


def test_format_rating_dividend_value_present():
    r = make_rating()
    out = format_rating(r)
    # 2.5% Dividende sollte in der Tabelle stehen
    assert "2.5%" in out


def test_format_rating_handles_none_dividend():
    """None dividend_yield_pct → 'n/a' (kein Crash)."""
    fund = make_fund(div_yield=None)
    r = make_rating(fund=fund)
    out = format_rating(r)
    assert "n/a" in out


def test_format_rating_handles_none_recommendation():
    fund = make_fund(recommendation=None)
    r = make_rating(fund=fund)
    out = format_rating(r)
    assert "n/a" in out


def test_format_rating_reasons_section():
    r = make_rating(reasons=["Bullish", "Oversold", "Fib Goldilocks"])
    out = format_rating(r)
    assert "## Begründung" in out
    assert "Bullish" in out


def test_format_rating_no_reasons_section():
    r = make_rating(reasons=[])
    out = format_rating(r)
    assert "Keine besonders starken Signale" in out


# ============================================================
# format_table
# ============================================================

def test_format_table_sorts_descending():
    r_a = make_rating(total_score=80, grade="A")
    r_b = make_rating(total_score=50, grade="C")
    out = format_table([r_b, r_a])
    # Höherer Score zuerst
    pos_a = out.find("**A**")
    pos_c = out.find("**C**")
    assert pos_a < pos_c, f"Format table should sort by score desc, but A pos={pos_a} > C pos={pos_c}"


def test_format_table_handles_none_values():
    fund = make_fund(price=None, kgv=None, kbv=None, fair_margin=None)
    r = make_rating(fund=fund)
    out = format_table([r])
    assert "n/a" in out


# ============================================================
# format_compact (Telegram)
# ============================================================

def test_format_compact_one_line():
    r = make_rating()
    out = format_compact(r)
    lines = out.strip().split("\n")
    assert len(lines) == 1, f"Compact format muss 1 Zeile sein, war {len(lines)}: {out!r}"


def test_format_compact_contains_key_info():
    r = make_rating()
    out = format_compact(r)
    # Symbol, Grade, Score, Preis, RSI, Trend
    assert "TEST" in out
    assert "A" in out
    assert "STRONG BUY" in out
    assert "RSI" in out
    assert "100" in out or "100.00" in out  # Preis


def test_format_compact_handles_none_price():
    fund = make_fund(price=None)
    r = make_rating(fund=fund)
    out = format_compact(r)
    assert "n/a" in out
    # Sollte nicht crashen
    assert len(out) > 0


def test_format_compact_table_sorted():
    r_a = make_rating(total_score=80, grade="A", action="STRONG BUY")
    r_b = make_rating(total_score=50, grade="C", action="HOLD")
    out = format_compact_table([r_b, r_a])
    lines = out.split("\n")
    pos_a = next(i for i, l in enumerate(lines) if "STRONG BUY" in l)
    pos_c = next(i for i, l in enumerate(lines) if "HOLD" in l and "STRONG" not in l)
    assert pos_a < pos_c, f"Sortierung falsch: A pos={pos_a} > C pos={pos_c}\n{out}"


# ============================================================
# rate_many
# ============================================================

def test_rate_many_continues_on_failure():
    """Ein Fehler bei einem Symbol crasht nicht die ganze Liste."""
    from stockscheck.rater import rate_many
    from unittest.mock import patch
    with patch("stockscheck.rater.rate_one") as mock:
        mock.side_effect = [
            Exception("Boom"),
            make_rating(),
        ]
        ratings = rate_many(["BAD", "GOOD"])
        assert len(ratings) == 1


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
