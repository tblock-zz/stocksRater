"""Tests für Indicator-Scoring-Funktionen (deterministisch, ohne yfinance)."""
import sys
from pathlib import Path
from dataclasses import dataclass
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from stockscheck.indicators import trend_score, rsi_score, macd_score, stoch_score
from stockscheck.fibonacci import FibResult


def make_tech(**overrides):
    """Erstellt ein minimales TechnicalResult-Dummy für Scorer-Tests."""
    defaults = dict(
        symbol="X", last_price=100, last_date=pd.Timestamp("2025-01-01"),
        sma50=100, sma200=100, sma50_vs_sma200_pct=0,
        trend="up", golden_cross_recent=False, death_cross_recent=False,
        rsi=50, rsi_signal="neutral",
        macd=0, macd_signal=0, macd_diff=0, macd_trend="flat",
        stoch_k=50, stoch_slow=50, stoch_signal="neutral",
        bb_upper=110, bb_lower=90, bb_position=0.5, bb_signal="middle",
        fib=FibResult(0,0,pd.Timestamp("2025-01-01"),pd.Timestamp("2025-01-01"),"up",{},0,0,0,0),
    )
    defaults.update(overrides)
    return type("T", (), defaults)()


def test_rsi_oversold_top_score():
    t = make_tech(rsi=20)
    assert rsi_score(t) == 10.0


def test_rsi_overbought_zero():
    t = make_tech(rsi=80)
    assert rsi_score(t) == 0.0


def test_rsi_buy_zone_high_score():
    t = make_tech(rsi=27)
    assert rsi_score(t) == 9.0


def test_rsi_neutral_mid():
    t = make_tech(rsi=45)
    assert rsi_score(t) == 5.0


def test_trend_strong_uptrend():
    t = make_tech(sma50=110, sma200=100, sma50_vs_sma200_pct=10)
    assert trend_score(t) == 15.0


def test_trend_golden_cross():
    t = make_tech(sma50=102, sma200=100, sma50_vs_sma200_pct=2)
    assert trend_score(t) == 12.0


def test_trend_death_cross():
    t = make_tech(sma50=98, sma200=100, sma50_vs_sma200_pct=-2)
    assert trend_score(t) == 5.0


def test_trend_strong_downtrend():
    t = make_tech(sma50=85, sma200=100, sma50_vs_sma200_pct=-15)
    assert trend_score(t) == 2.0


def test_macd_rising_bullish():
    t = make_tech(macd=2, macd_signal=1, macd_diff=0.5, macd_trend="rising")
    assert macd_score(t) == 10.0


def test_macd_falling_bearish():
    t = make_tech(macd=-2, macd_signal=-1, macd_diff=-0.5, macd_trend="falling")
    assert macd_score(t) == 1.0


def test_stoch_oversold_top():
    t = make_tech(stoch_slow=10)
    assert stoch_score(t) == 10.0


def test_stoch_overbought_zero():
    t = make_tech(stoch_slow=85)
    assert stoch_score(t) == 0.0


def test_stoch_buy_zone():
    t = make_tech(stoch_slow=30)
    assert stoch_score(t) == 7.0


if __name__ == "__main__":
    test_rsi_oversold_top_score(); print("✓ rsi_oversold_top")
    test_rsi_overbought_zero(); print("✓ rsi_overbought_zero")
    test_rsi_buy_zone_high_score(); print("✓ rsi_buy_zone")
    test_rsi_neutral_mid(); print("✓ rsi_neutral_mid")
    test_trend_strong_uptrend(); print("✓ trend_strong_uptrend")
    test_trend_golden_cross(); print("✓ trend_golden_cross")
    test_trend_death_cross(); print("✓ trend_death_cross")
    test_trend_strong_downtrend(); print("✓ trend_strong_downtrend")
    test_macd_rising_bullish(); print("✓ macd_rising_bullish")
    test_macd_falling_bearish(); print("✓ macd_falling_bearish")
    test_stoch_oversold_top(); print("✓ stoch_oversold_top")
    test_stoch_overbought_zero(); print("✓ stoch_overbought_zero")
    test_stoch_buy_zone(); print("✓ stoch_buy_zone")
    print("\nAll indicator tests passed.")