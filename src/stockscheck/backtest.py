"""Backtest: Bewertet die Vergangenheit — hätte unsere Strategie Gewinne gemacht?

Strategie:
- Kaufe wenn Score ≥60 (Grade B oder besser) bei Einstieg
- Verkaufe nach HOLD_DAYS oder wenn Score <45 (Grade C oder schlechter)
- Buy-and-Hold als Benchmark
- Walk-Forward: jeden MONAT eine neue Bewertung, handeln wenn nötig
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import List, Optional

try:
    from .stockscheck_bridge import loadTickerData
    from .indicators import build_technical
    from .fundamentals import fetch_fundamentals
    from scorer import build_rating, StockRating, score_to_grade
except ImportError:
    from .stockscheck_bridge import loadTickerData
    from .indicators import build_technical
    from .fundamentals import fetch_fundamentals
    from .scorer import build_rating, StockRating, score_to_grade


@dataclass
class Trade:
    symbol: str
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: Optional[pd.Timestamp]
    exit_price: Optional[float]
    entry_score: float
    exit_score: Optional[float]
    entry_grade: str
    exit_grade: Optional[str]
    return_pct: Optional[float]
    holding_days: Optional[int]
    exit_reason: str  # "hold_expired", "downgrade", "end_of_period"


@dataclass
class BacktestResult:
    symbol: str
    period_start: pd.Timestamp
    period_end: pd.Timestamp
    buy_hold_return_pct: float
    strategy_return_pct: float
    num_trades: int
    win_rate_pct: float
    avg_win_pct: float
    avg_loss_pct: float
    max_drawdown_pct: float
    trades: List[Trade] = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d["trades"] = [asdict(t) for t in self.trades]
        # Timestamps in Strings konvertieren für JSON
        d["period_start"] = str(self.period_start)
        d["period_end"] = str(self.period_end)
        for t in d["trades"]:
            t["entry_date"] = str(t["entry_date"])
            t["exit_date"] = str(t["exit_date"]) if t["exit_date"] else None
        return d


def score_at(symbol: str, df_slice: pd.DataFrame, target_date: pd.Timestamp) -> Optional[StockRating]:
    """Berechnet das Rating zu einem bestimmten historischen Zeitpunkt.

    Wir nutzen nur Preisdaten bis target_date (kein Look-Ahead-Bias).
    Fundamentaldaten sind leider nur aktuell von yfinance verfügbar —
    als Approximation verwenden wir die aktuellen Werte für alle historischen Zeitpunkte.
    (Das ist eine bekannte Limitation; für eine strenge Backtest müsste man
    historische Quarterly-Reports nutzen.)
    """
    if df_slice is None or len(df_slice) < 200:
        return None

    # Bewerte mit historischen Daten bis target_date
    try:
        tech = build_technical(symbol, df_slice)
    except Exception:
        return None

    # Fundamentaldaten: aktuelle Werte (Limitation — siehe Doc)
    fund = fetch_fundamentals(symbol)
    return build_rating(tech, fund)


def backtest_symbol(
    symbol: str,
    period: str = "5y",
    rebalance_days: int = 30,
    min_score_to_buy: float = 60.0,
    exit_score_threshold: float = 45.0,
    max_holding_days: int = 365,
) -> BacktestResult:
    """Backtest für ein einzelnes Symbol.

    Logik:
    - Jede `rebalance_days` Tage prüfen wir den Score
    - Wenn score >= min_score_to_buy: kaufen (falls nicht investiert)
    - Wenn investiert UND score < exit_score_threshold ODER holding > max_holding_days: verkaufen
    - Buy-and-Hold als Benchmark
    """
    df = loadTickerData(symbol, "1d")
    if len(df) < 250:
        return BacktestResult(
            symbol=symbol, period_start=df.index[0], period_end=df.index[-1],
            buy_hold_return_pct=0, strategy_return_pct=0, num_trades=0,
            win_rate_pct=0, avg_win_pct=0, avg_loss_pct=0, max_drawdown_pct=0,
        )

    period_start = df.index[0]
    period_end = df.index[-1]

    # Buy-and-Hold
    bh_return = (df["Close"].iloc[-1] / df["Close"].iloc[0] - 1) * 100

    # Strategy: jeden rebalance_days einen Score berechnen
    rebalance_dates = df.index[::rebalance_days]
    if len(rebalance_dates) < 2:
        rebalance_dates = df.index

    trades: List[Trade] = []
    in_position = False
    entry_price = 0.0
    entry_date = None
    entry_score = 0.0
    entry_grade = ""
    entry_idx = 0  # Index in df

    for i, date in enumerate(rebalance_dates):
        df_slice = df.loc[:date]
        if len(df_slice) < 200:
            continue

        rating = score_at(symbol, df_slice, date)
        if rating is None:
            continue

        score = rating.total_score
        grade = rating.grade

        if not in_position:
            if score >= min_score_to_buy:
                # Kaufen
                entry_price = float(df.loc[date, "Close"]) if date in df.index else rating.technical.last_price
                entry_date = date
                entry_score = score
                entry_grade = grade
                entry_idx = df.index.get_loc(date) if date in df.index else -1
                in_position = True
        else:
            # Position offen: prüfen Exit-Bedingungen
            current_idx = df.index.get_loc(date) if date in df.index else -1
            holding = (date - entry_date).days if entry_date else 0

            exit_reason = None
            if score < exit_score_threshold:
                exit_reason = "downgrade"
            elif holding >= max_holding_days:
                exit_reason = "hold_expired"

            if exit_reason:
                exit_price = float(df.loc[date, "Close"]) if date in df.index else rating.technical.last_price
                ret_pct = (exit_price / entry_price - 1) * 100
                trades.append(Trade(
                    symbol=symbol,
                    entry_date=entry_date,
                    entry_price=entry_price,
                    exit_date=date,
                    exit_price=exit_price,
                    entry_score=entry_score,
                    exit_score=score,
                    entry_grade=entry_grade,
                    exit_grade=grade,
                    return_pct=ret_pct,
                    holding_days=holding,
                    exit_reason=exit_reason,
                ))
                in_position = False

    # Offene Position am Ende schließen
    if in_position:
        exit_price = float(df["Close"].iloc[-1])
        holding = (df.index[-1] - entry_date).days
        ret_pct = (exit_price / entry_price - 1) * 100
        trades.append(Trade(
            symbol=symbol,
            entry_date=entry_date,
            entry_price=entry_price,
            exit_date=df.index[-1],
            exit_price=exit_price,
            entry_score=entry_score,
            exit_score=None,
            entry_grade=entry_grade,
            exit_grade=None,
            return_pct=ret_pct,
            holding_days=holding,
            exit_reason="end_of_period",
        ))

    # Strategie-Return: geometrisch (Compounding) über die nicht-überlappenden
    # Trade-Perioden. Additive Summierung würde bei Verlust-Trades systematisch
    # zu hohe Returns ausweisen (z.B. -50%, +50% additiv = 0%, real = -25%).
    if trades:
        valid_rets = [t.return_pct for t in trades if t.return_pct is not None]
        if valid_rets:
            # echtes Compounding: prod(1 + r_i/100) - 1, in Prozent
            growth = 1.0
            for r in valid_rets:
                growth *= 1.0 + r / 100.0
            strategy_return = (growth - 1.0) * 100
        else:
            strategy_return = 0.0
    else:
        # Keine Trades = Buy-and-Hold (oder 0)
        strategy_return = 0.0

    # Win-Rate
    wins = [t.return_pct for t in trades if t.return_pct is not None and t.return_pct > 0]
    losses = [t.return_pct for t in trades if t.return_pct is not None and t.return_pct <= 0]
    win_rate = (len(wins) / len(trades) * 100) if trades else 0
    avg_win = np.mean(wins) if wins else 0
    avg_loss = np.mean(losses) if losses else 0

    # Max Drawdown der Strategie (sequenziell)
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in trades:
        if t.return_pct is not None:
            cum += t.return_pct
            peak = max(peak, cum)
            dd = peak - cum
            max_dd = max(max_dd, dd)

    return BacktestResult(
        symbol=symbol,
        period_start=period_start,
        period_end=period_end,
        buy_hold_return_pct=bh_return,
        strategy_return_pct=strategy_return,
        num_trades=len(trades),
        win_rate_pct=win_rate,
        avg_win_pct=avg_win,
        avg_loss_pct=avg_loss,
        max_drawdown_pct=max_dd,
        trades=trades,
    )


def backtest_portfolio(symbols: List[str], period: str = "5y", **kwargs) -> dict:
    """Backtest für mehrere Symbole."""
    results = []
    for sym in symbols:
        try:
            r = backtest_symbol(sym, period=period, **kwargs)
            results.append(r)
        except Exception as e:
            print(f"[WARN] backtest {sym}: {e}")

    if not results:
        return {"results": [], "summary": {}}

    avg_bh = np.mean([r.buy_hold_return_pct for r in results])
    avg_strat = np.mean([r.strategy_return_pct for r in results])
    avg_wr = np.mean([r.win_rate_pct for r in results])
    total_trades = sum(r.num_trades for r in results)

    return {
        "results": [r.to_dict() for r in results],
        "summary": {
            "symbols_tested": len(results),
            "avg_buy_hold_return_pct": avg_bh,
            "avg_strategy_return_pct": avg_strat,
            "avg_win_rate_pct": avg_wr,
            "total_trades": total_trades,
            "strategy_outperforms": avg_strat > avg_bh,
        },
    }