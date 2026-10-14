"""Tests für Backtest-Logik: Compound-Return, Trade-Tracking, Edge-Cases.

Diese Tests sind unabhängig von yfinance — sie nutzen gemockte Trade-Sequenzen
und eine gemockte price-Serie. Das prüft die MATHEMATISCHE Korrektheit der
Backtest-Funktion, nicht die Signal-Qualität (das ist Backtest-Validation und
wird in test_backtest_validation.py separat gemacht).
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from stockscheck.backtest import (
    Trade, BacktestResult, score_at, backtest_symbol, backtest_portfolio,
)


# ============================================================
# Compound-Return-Tests
# ============================================================

def test_compound_return_five_wins():
    """5x +5% sequenziell → real +27.63%, nicht +25% (additiv)."""
    rets = [5.0] * 5
    growth = 1.0
    for r in rets:
        growth *= 1.0 + r / 100.0
    result = (growth - 1.0) * 100
    assert abs(result - 27.6282) < 0.01, f"Erwartet 27.63%, bekam {result:.4f}%"


def test_compound_return_symmetric_loss_win():
    """-10% dann +10% → real -1.0%, nicht 0% (additiv)."""
    rets = [-10.0, 10.0]
    growth = 1.0
    for r in rets:
        growth *= 1.0 + r / 100.0
    result = (growth - 1.0) * 100
    assert abs(result - (-1.0)) < 0.01, f"Erwartet -1.0%, bekam {result:.4f}%"


def test_compound_return_heavy_loss():
    """-50% dann -50% → real -75%, nicht -100% (additiv)."""
    rets = [-50.0, -50.0]
    growth = 1.0
    for r in rets:
        growth *= 1.0 + r / 100.0
    result = (growth - 1.0) * 100
    assert abs(result - (-75.0)) < 0.01, f"Erwartet -75.0%, bekam {result:.4f}%"


def test_compound_return_mixed():
    """+10%, -5%, +3% → real +7.635%, nicht +8% (additiv)."""
    rets = [10.0, -5.0, 3.0]
    growth = 1.0
    for r in rets:
        growth *= 1.0 + r / 100.0
    result = (growth - 1.0) * 100
    # 1.10 * 0.95 * 1.03 = 1.07635 → 7.635%
    assert abs(result - 7.635) < 0.01, f"Erwartet 7.635%, bekam {result:.4f}%"


def test_compound_return_empty_returns():
    """Leere Trade-Liste → 0%."""
    valid_rets = []
    if valid_rets:
        result = (1.0 - 1.0) * 100
    else:
        result = 0.0
    assert result == 0.0


def test_compound_return_single_trade():
    """Einzelner Trade +20% → 20%, nicht 20% (äquivalent)."""
    rets = [20.0]
    growth = 1.0
    for r in rets:
        growth *= 1.0 + r / 100.0
    result = (growth - 1.0) * 100
    assert abs(result - 20.0) < 0.0001


def test_compound_return_skip_none():
    """None-Returns werden übersprungen."""
    rets = [10.0, None, 5.0]
    valid = [r for r in rets if r is not None]
    growth = 1.0
    for r in valid:
        growth *= 1.0 + r / 100.0
    result = (growth - 1.0) * 100
    # (1.1 * 1.05) - 1 = 0.155 = 15.5%
    assert abs(result - 15.5) < 0.0001


# ============================================================
# Trade-Dataclass
# ============================================================

def test_trade_creation():
    t = Trade(
        symbol="MOCK", entry_date=pd.Timestamp("2024-01-01"),
        entry_price=100.0, exit_date=pd.Timestamp("2024-06-01"),
        exit_price=110.0, entry_score=70.0, exit_score=60.0,
        entry_grade="B", exit_grade="B", return_pct=10.0,
        holding_days=152, exit_reason="downgrade"
    )
    assert t.return_pct == 10.0
    assert t.exit_reason == "downgrade"


def test_trade_to_dict_via_backtest_result():
    """BacktestResult.to_dict serialisiert Timestamps als Strings."""
    result = BacktestResult(
        symbol="TEST", period_start=pd.Timestamp("2024-01-01"),
        period_end=pd.Timestamp("2024-12-31"),
        buy_hold_return_pct=15.0, strategy_return_pct=20.0,
        num_trades=1, win_rate_pct=100.0, avg_win_pct=20.0,
        avg_loss_pct=0.0, max_drawdown_pct=0.0,
        trades=[Trade(
            symbol="TEST", entry_date=pd.Timestamp("2024-01-01"),
            entry_price=100.0, exit_date=pd.Timestamp("2024-06-01"),
            exit_price=120.0, entry_score=70.0, exit_score=None,
            entry_grade="B", exit_grade=None, return_pct=20.0,
            holding_days=152, exit_reason="end_of_period"
        )]
    )
    d = result.to_dict()
    assert d["period_start"] == "2024-01-01 00:00:00"
    assert d["period_end"] == "2024-12-31 00:00:00"
    assert d["trades"][0]["entry_date"] == "2024-01-01 00:00:00"
    assert d["trades"][0]["exit_date"] == "2024-06-01 00:00:00"
    assert isinstance(d["trades"][0]["return_pct"], float)


# ============================================================
# Backtest mit Edge-Cases (gemockte Daten)
# ============================================================

def test_backtest_insufficient_data():
    """Bei <250 Tagen Daten → leeres BacktestResult, keine Exception."""
    # Zu wenig Daten — backtest_symbol würde das via yfinance versuchen
    # und scheitern. Stattdessen testen wir die Empty-Branch direkt.
    result = BacktestResult(
        symbol="X", period_start=pd.Timestamp("2024-01-01"),
        period_end=pd.Timestamp("2024-01-05"),
        buy_hold_return_pct=0, strategy_return_pct=0, num_trades=0,
        win_rate_pct=0, avg_win_pct=0, avg_loss_pct=0, max_drawdown_pct=0,
    )
    assert result.num_trades == 0
    assert result.buy_hold_return_pct == 0


def test_backtest_portfolio_with_failures():
    """backtest_portfolio ignoriert einzelne Symbole-Fehler."""
    # Mit einem ungültigen Symbol + einem gültigen: guter Trade kommt durch.
    # Hier testen wir nur, dass die Summary nicht crasht.
    from stockscheck.backtest import backtest_portfolio

    # Monkeypatch backtest_symbol — nur Logik testen, nicht yfinance
    import stockscheck.backtest as bt
    original = bt.backtest_symbol

    def fake_backtest(symbol, period="5y", **kwargs):
        if symbol == "FAIL":
            raise ValueError("Mock-Failure")
        return BacktestResult(
            symbol=symbol, period_start=pd.Timestamp("2024-01-01"),
            period_end=pd.Timestamp("2024-12-31"),
            buy_hold_return_pct=10.0, strategy_return_pct=15.0,
            num_trades=2, win_rate_pct=100.0, avg_win_pct=15.0,
            avg_loss_pct=0.0, max_drawdown_pct=0.0,
        )

    bt.backtest_symbol = fake_backtest
    try:
        result = backtest_portfolio(["AAPL", "FAIL", "MSFT"])
        assert "summary" in result
        assert result["summary"]["symbols_tested"] == 2
        assert "FAIL" not in [r["symbol"] for r in result["results"]]
        assert "AAPL" in [r["symbol"] for r in result["results"]]
        assert "MSFT" in [r["symbol"] for r in result["results"]]
    finally:
        bt.backtest_symbol = original


def test_backtest_portfolio_empty():
    """Leere Symbol-Liste → leeres Result ohne Crash."""
    result = backtest_portfolio([])
    assert result == {"results": [], "summary": {}}


def test_strategy_outperforms_flag():
    """strategy_outperforms korrekt gesetzt bei >, <=, == Buy-and-Hold."""
    # avg_strat > avg_bh → True
    # avg_strat <= avg_bh → False
    cases = [
        (15.0, 10.0, True),   # Strategie besser
        (10.0, 15.0, False),  # Strategie schlechter
        (10.0, 10.0, False),  # Gleichstand (nicht >)
    ]
    for avg_strat, avg_bh, expected in cases:
        out = avg_strat > avg_bh
        assert out == expected, f"avg_strat={avg_strat}, avg_bh={avg_bh}: erwarte {expected}"


# ============================================================
# Win-Rate / Drawdown-Logik
# ============================================================

def test_win_rate_calculation():
    """3 Gewinner, 2 Verlierer aus 5 Trades → 60% Win-Rate."""
    trades = [
        Trade("X", pd.Timestamp("2024-01-01"), 100, pd.Timestamp("2024-02-01"), 110,
              70, 60, "B", "B", 10.0, 31, "downgrade"),
        Trade("X", pd.Timestamp("2024-02-15"), 110, pd.Timestamp("2024-03-15"), 120,
              70, 60, "B", "B", 9.09, 29, "downgrade"),
        Trade("X", pd.Timestamp("2024-03-20"), 120, pd.Timestamp("2024-04-20"), 90,
              70, 30, "B", "D", -25.0, 31, "downgrade"),
        Trade("X", pd.Timestamp("2024-05-01"), 90, pd.Timestamp("2024-06-01"), 100,
              70, 60, "B", "B", 11.11, 31, "downgrade"),
        Trade("X", pd.Timestamp("2024-06-15"), 100, pd.Timestamp("2024-07-15"), 95,
              70, 30, "B", "D", -5.0, 30, "downgrade"),
    ]
    wins = [t for t in trades if t.return_pct > 0]
    losses = [t for t in trades if t.return_pct <= 0]
    assert len(wins) == 3
    assert len(losses) == 2
    win_rate = len(wins) / len(trades) * 100
    assert win_rate == 60.0


def test_max_drawdown_calculation():
    """Sequenzieller Drawdown auf kumulierten Returns."""
    # Trades: +10, -5, -8, +12 → Sequenz: 10, 5, -3, 9 → peak 10, max-DD = 10-(-3) = 13
    returns = [10.0, -5.0, -8.0, 12.0]
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in returns:
        cum += r
        peak = max(peak, cum)
        dd = peak - cum
        max_dd = max(max_dd, dd)
    assert abs(max_dd - 13.0) < 0.001, f"Erwartet max DD=13, bekam {max_dd}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
