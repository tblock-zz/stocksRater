"""Tests für Fibonacci-Retracements mit deterministischen Inputs.

Wichtig: lookback=60 nutzt die letzten 60 Einträge. Die Tests
bauen Daten so, dass die Lookback-Region klar einen Trend zeigt.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from stockscheck.fibonacci import (
    analyze, find_swing_points, compute_fib_levels, fib_score
)


def make_df(prices):
    """Erstellt einen DataFrame mit den gegebenen Preisen."""
    n = len(prices)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    df = pd.DataFrame({
        "Open": prices,
        "High": [p * 1.01 for p in prices],
        "Low":  [p * 0.99 for p in prices],
        "Close": prices,
        "Volume": [1_000_000] * n,
    }, index=dates)
    return df


def test_uptrend_goldilocks_score_10():
    """Aufwärtstrend in Lookback-Region, Preis in Goldilocks-Zone → 10."""
    # Lookback (60 Werte): Tief bei 100 → Hoch bei 200, dann Preis auf 150 (Goldilocks)
    # Wir bauen die letzten 60 Werte:
    # 30 Tage Aufstieg 100→200, dann 30 Tage seitwärts/leichter Rückgang auf 150
    rise = list(range(100, 200, 3))  # 34 Werte: 100, 103, ..., 199
    # Sicherstellen dass wir das Hoch bei 200 haben
    rise.append(200)
    # Konsolidierung auf 150
    consolidation = [150 + (i % 5 - 2) for i in range(25)]
    prices = [80 + i for i in range(20)] + rise + consolidation
    # Lookback = letzte 60
    df = make_df(prices[-60:])
    fib = analyze(df, lookback=60)
    assert fib.trend == "up", f"Expected up-trend, got {fib.trend} (price={fib.current_price})"
    # 200 - 100*0.382 = 161.8, 200 - 100*0.618 = 138.2, Goldilocks: 138.2 ≤ 150 ≤ 161.8
    score, _, _, _ = fib_score(fib.current_price, fib.levels, fib.trend)
    assert score == 10.0, f"Expected 10 (Goldilocks), got {score} for price={fib.current_price}, levels={fib.levels}"


def test_downtrend_returns_zero():
    """Abwärtstrend in Lookback → Score 0."""
    # Letzte 60 Tage: 200 → 100 (Abwärtstrend)
    fall = [200 - i for i in range(60)]
    fall[-1] = 110  # Endpreis
    df = make_df(fall)
    fib = analyze(df, lookback=60)
    assert fib.trend == "down", f"Expected down, got {fib.trend}"
    score, _, _, _ = fib_score(fib.current_price, fib.levels, fib.trend)
    assert score == 0.0


def test_uptrend_high_price_score_3():
    """Aufwärtstrend, Preis > 23.6% (neue Hochs) → Score 3."""
    # 100 → 200, dann weiter auf 195 (über 23.6% = 176.4)
    rise = list(range(100, 200, 3))
    rise.append(200)
    # Weiterer Anstieg
    continuation = [195] * 25
    prices = [80 + i for i in range(20)] + rise + continuation
    df = make_df(prices[-60:])
    fib = analyze(df, lookback=60)
    assert fib.trend == "up", f"Expected up, got {fib.trend}"
    score, _, _, _ = fib_score(fib.current_price, fib.levels, fib.trend)
    assert score == 3.0, f"Expected 3 (new highs), got {score}"


def test_uptrend_early_entry_score_8():
    """Aufwärtstrend, Preis zwischen 23.6% und 38.2% → Score 8."""
    # 100 → 200, Preis auf 170 (zwischen 161.8 und 176.4)
    rise = list(range(100, 200, 3))
    rise.append(200)
    consolidation = [170 + (i % 3 - 1) for i in range(25)]
    prices = [80 + i for i in range(20)] + rise + consolidation
    df = make_df(prices[-60:])
    fib = analyze(df, lookback=60)
    assert fib.trend == "up", f"Expected up, got {fib.trend}"
    # 23.6% = 176.4, 38.2% = 161.8. 170 liegt dazwischen.
    score, _, _, _ = fib_score(fib.current_price, fib.levels, fib.trend)
    assert score == 8.0, f"Expected 8, got {score} for price={fib.current_price}"


def test_fib_levels_correct_values():
    """Prüft exakte Fib-Level-Berechnung."""
    levels = compute_fib_levels(swing_high=200, swing_low=100, trend="up")
    assert levels[0.0] == 200.0
    assert levels[0.236] == 200 - 100 * 0.236  # 176.4
    assert levels[0.382] == 200 - 100 * 0.382  # 161.8
    assert levels[0.5]   == 200 - 100 * 0.5    # 150.0
    assert levels[0.618] == 200 - 100 * 0.618  # 138.2
    assert levels[0.786] == 200 - 100 * 0.786  # 121.4
    assert levels[1.0]   == 100.0


def test_analyze_returns_dataclass():
    """analyze() liefert ein vollständiges FibResult-Objekt."""
    rise = list(range(100, 200, 3))
    rise.append(200)
    consolidation = [180] * 25
    prices = [80 + i for i in range(20)] + rise + consolidation
    df = make_df(prices[-60:])
    fib = analyze(df, lookback=60)
    assert fib.swing_high >= 199
    assert fib.swing_low <= 110
    assert fib.trend in ("up", "down")
    assert 0.382 in fib.levels
    assert fib.current_price > 0


if __name__ == "__main__":
    test_uptrend_goldilocks_score_10(); print("✓ uptrend_goldilocks")
    test_downtrend_returns_zero(); print("✓ downtrend_zero")
    test_uptrend_high_price_score_3(); print("✓ uptrend_high")
    test_uptrend_early_entry_score_8(); print("✓ uptrend_early")
    test_fib_levels_correct_values(); print("✓ fib_levels")
    test_analyze_returns_dataclass(); print("✓ analyze_returns")
    print("\nAll fibonacci tests passed.")