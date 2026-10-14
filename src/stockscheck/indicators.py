"""Technical-Indicators-Wrapper um die stocksCheck-Berechnungen.

Wir nehmen calculateIndicators(df) und extrahieren Bewertungen für:
- Trend (SMA50 vs SMA200, Cross)
- RSI (14)
- MACD (12,26,9)
- Stochastik (16,3,3)
- Bollinger (Position)
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import pandas as pd

try:
    from .stockscheck_bridge import (
        calculateIndicators,
        isRsiBelow, isRsiAbove,
        isStochasticSlowAbove, isStochasticSlowBelow,
        isMacdRising, isMacdFalling,
        isCrossEma50Ema200Up, isCrossEma50Ema200Down,
        isCloseBelowLowerBoellingerBand, isCloseAboveUpperBoellingerBand,
    )
    from .fibonacci import analyze as fib_analyze, FibResult
except ImportError:
    from .stockscheck_bridge import (
        calculateIndicators,
        isRsiBelow, isRsiAbove,
        isStochasticSlowAbove, isStochasticSlowBelow,
        isMacdRising, isMacdFalling,
        isCrossEma50Ema200Up, isCrossEma50Ema200Down,
        isCloseBelowLowerBoellingerBand, isCloseAboveUpperBoellingerBand,
    )
    from .fibonacci import analyze as fib_analyze, FibResult


@dataclass
class TechnicalResult:
    symbol: str
    last_price: float
    last_date: pd.Timestamp
    sma50: float
    sma200: float
    sma50_vs_sma200_pct: float  # (sma50/sma200 - 1) * 100
    trend: str  # "up", "down", "sideways"
    golden_cross_recent: bool  # True wenn in den letzten 50 Tagen
    death_cross_recent: bool
    rsi: float
    rsi_signal: str  # "oversold", "buy_zone", "neutral", "overbought"
    macd: float
    macd_signal: float
    macd_diff: float
    macd_trend: str  # "rising", "falling", "flat"
    stoch_k: float
    stoch_slow: float
    stoch_signal: str  # "oversold", "buy_zone", "neutral", "overbought"
    bb_upper: float
    bb_lower: float
    bb_position: float  # (last - lower) / (upper - lower) → 0=unter BB, 1=über BB
    bb_signal: str  # "below_lower", "lower_half", "middle", "upper_half", "above_upper"
    fib: FibResult
    # Sub-Scores (vom Scorer befüllt)
    sub_score_trend: float = 0.0
    sub_score_rsi: float = 0.0
    sub_score_macd: float = 0.0
    sub_score_stoch: float = 0.0
    sub_score_fib: float = 0.0
    notes: list = None

    def __post_init__(self):
        if self.notes is None:
            self.notes = []


def trend_score(t: TechnicalResult) -> float:
    """Trend-Subscore: SMA50 vs SMA200. Max 15 Punkte.

    sma50 > sma200 und Distanz > +5% = 15 (starker Aufwärtstrend)
    sma50 > sma200 (Golden Cross aktiv) = 12
    sma50 < sma200 (Death Cross aktiv) = 0-3
    Golden Cross in letzten 50 Tagen = Bonus bereits in 12 drin
    """
    if t.sma50 > t.sma200:
        diff_pct = (t.sma50 / t.sma200 - 1) * 100
        if diff_pct > 5:
            return 15.0
        elif diff_pct > 0:
            return 12.0
        else:
            return 10.0
    else:
        diff_pct = (t.sma50 / t.sma200 - 1) * 100
        # Floating-Point-Toleranz: (85/100-1)*100 = -15.000000000000002, nicht exakt -15
        # Wir nutzen Toleranz: diff_pct ist "nahe -X" wenn |diff_pct - (-X)| < 1
        if diff_pct > -5:
            return 5.0
        elif abs(diff_pct - (-15)) < 1 or diff_pct > -15:
            return 2.0
        else:
            return 0.0


def rsi_score(t: TechnicalResult) -> float:
    """RSI-Subscore. Max 10 Punkte.

    <25 = 10 (extrem überverkauft — Bodenbildung)
    25-30 = 9
    30-40 = 8 (Buy-Zone)
    40-50 = 5 (neutral)
    50-60 = 4
    60-70 = 2 (Vorsicht)
    >70 = 0 (überkauft)
    """
    rsi = t.rsi
    if rsi < 25:
        return 10.0
    elif rsi < 30:
        return 9.0
    elif rsi < 40:
        return 8.0
    elif rsi < 50:
        return 5.0
    elif rsi < 60:
        return 4.0
    elif rsi < 70:
        return 2.0
    else:
        return 0.0


def macd_score(t: TechnicalResult) -> float:
    """MACD-Subscore. Max 10 Punkte.

    Histogram steigend UND MACD > Signal = 10
    Histogram steigend (über Null) = 8
    Histogram steigend (unter Null) = 7 (Trendwende)
    Histogram fallend (über Null) = 3
    Histogram fallend (unter Null) = 1
    """
    diff = t.macd_diff
    macd = t.macd
    sig = t.macd_signal

    if t.macd_trend == "rising":
        if macd > sig:
            return 10.0
        elif macd > 0:
            return 8.0
        else:
            return 7.0
    else:  # falling
        if macd > 0:
            return 3.0
        else:
            return 1.0


def stoch_score(t: TechnicalResult) -> float:
    """Stochastik-Subscore. Max 10 Punkte.

    <15 = 10 (extrem überverkauft)
    15-25 = 9
    25-40 = 7 (Buy-Zone)
    40-60 = 5 (neutral)
    60-80 = 3
    >80 = 0 (überkauft)
    """
    s = t.stoch_slow
    if pd.isna(s):
        return 0.0
    if s < 15:
        return 10.0
    elif s < 25:
        return 9.0
    elif s < 40:
        return 7.0
    elif s < 60:
        return 5.0
    elif s < 80:
        return 3.0
    else:
        return 0.0


def fib_to_score_impl(fib: FibResult) -> float:
    """Direkter Wrapper ohne zirkulären Import. Spiegel fib_score() aus fibonacci.py."""
    if fib.trend == "down":
        return 0.0
    price = fib.current_price
    levels = fib.levels
    if not levels or price == 0:
        return 0.0

    l_236 = levels.get(0.236, 0)
    l_382 = levels.get(0.382, 0)
    l_500 = levels.get(0.5, 0)
    l_618 = levels.get(0.618, 0)
    l_786 = levels.get(0.786, 0)

    # Aufwärtstrend: levels absteigend (0.0=High oben, 1.0=Low unten)
    if l_618 <= price <= l_382:
        return 10.0  # Goldilocks
    elif price > l_382:
        if price <= l_236:
            return 8.0
        else:
            return 3.0
    else:
        if price >= l_786:
            return 5.0
        else:
            return 2.0


def build_technical(symbol: str, df: pd.DataFrame) -> TechnicalResult:
    """Baut die TechnicalResult aus einem DataFrame mit berechneten Indicators."""
    if df is None or len(df) < 200:
        raise ValueError(f"Not enough data for {symbol}: {len(df) if df is not None else 0} rows (need ≥200)")

    df_ind = calculateIndicators(df.copy())
    last = df_ind.iloc[-1]
    last_idx = df_ind.index[-1]

    # Trend
    sma50 = float(last["Ma50"])
    sma200 = float(last["Ma200"])
    diff_pct = (sma50 / sma200 - 1) * 100 if sma200 else 0

    # Golden/Death Cross in den letzten 50 Tagen?
    golden_recent = False
    death_recent = False
    window = df_ind.iloc[-51:]  # 50 Übergänge
    for i in range(1, len(window)):
        try:
            if isCrossEma50Ema200Up(window, i):
                golden_recent = True
            if isCrossEma50Ema200Down(window, i):
                death_recent = True
        except Exception:
            pass

    if sma50 > sma200 * 1.005:
        trend = "up"
    elif sma50 < sma200 * 0.995:
        trend = "down"
    else:
        trend = "sideways"

    # RSI
    rsi = float(last["RSI"])
    if rsi < 30:
        rsi_sig = "oversold"
    elif rsi < 40:
        rsi_sig = "buy_zone"
    elif rsi < 60:
        rsi_sig = "neutral"
    elif rsi < 70:
        rsi_sig = "warm"
    else:
        rsi_sig = "overbought"

    # MACD
    macd = float(last["Macd"])
    macd_sig = float(last["MacdSig"])
    macd_d = float(last["MacdDif"])
    if macd_d > 0.05:
        macd_trend = "rising"
    elif macd_d < -0.05:
        macd_trend = "falling"
    else:
        macd_trend = "flat"

    # Stochastik
    stoch_k = float(last["stoch_k"]) if "stoch_k" in df_ind.columns else float("nan")
    stoch_slow = float(last["StMa"]) if "StMa" in df_ind.columns else float("nan")
    if stoch_slow < 20:
        stoch_sig = "oversold"
    elif stoch_slow < 40:
        stoch_sig = "buy_zone"
    elif stoch_slow < 60:
        stoch_sig = "neutral"
    elif stoch_slow < 80:
        stoch_sig = "warm"
    else:
        stoch_sig = "overbought"

    # Bollinger
    bb_u = float(last["BbUpper"])
    bb_l = float(last["BbLower"])
    price = float(last["Close"])
    bb_range = bb_u - bb_l if bb_u != bb_l else 1
    bb_pos = (price - bb_l) / bb_range
    if bb_pos < 0:
        bb_sig = "below_lower"
    elif bb_pos < 0.3:
        bb_sig = "lower_half"
    elif bb_pos < 0.7:
        bb_sig = "middle"
    elif bb_pos < 1.0:
        bb_sig = "upper_half"
    else:
        bb_sig = "above_upper"

    # Fibonacci
    fib = fib_analyze(df_ind, lookback=60)

    return TechnicalResult(
        symbol=symbol,
        last_price=price,
        last_date=last_idx,
        sma50=sma50,
        sma200=sma200,
        sma50_vs_sma200_pct=diff_pct,
        trend=trend,
        golden_cross_recent=golden_recent,
        death_cross_recent=death_recent,
        rsi=rsi,
        rsi_signal=rsi_sig,
        macd=macd,
        macd_signal=macd_sig,
        macd_diff=macd_d,
        macd_trend=macd_trend,
        stoch_k=stoch_k,
        stoch_slow=stoch_slow,
        stoch_signal=stoch_sig,
        bb_upper=bb_u,
        bb_lower=bb_l,
        bb_position=bb_pos,
        bb_signal=bb_sig,
        fib=fib,
    )


def score_technical(t: TechnicalResult) -> None:
    """Befüllt Sub-Scores in-place."""
    t.sub_score_trend = trend_score(t)
    t.sub_score_rsi = rsi_score(t)
    t.sub_score_macd = macd_score(t)
    t.sub_score_stoch = stoch_score(t)
    t.sub_score_fib = fib_to_score_impl(t.fib)