"""Fibonacci-Retracements aus Swing-High/Low der letzten N Perioden.

Retracement-Levels: 23.6%, 38.2%, 50%, 61.8%, 78.6%
- 38.2% / 50% / 61.8% sind die klassischen Support-/Resistance-Zonen
- Aktueller Kurs nahe 61.8% in einem Aufwärtstrend = gutes Einstiegs-Level
- Aktueller Kurs nahe 23.6% = frühes Einstiegs-Level
- Aktueller Kurs > 100% = neue Hochs (Trend intakt, aber teuer)
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass


FIB_LEVELS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]


@dataclass
class FibResult:
    swing_high: float
    swing_low: float
    swing_high_idx: pd.Timestamp
    swing_low_idx: pd.Timestamp
    trend: str  # "up" (low→high) oder "down" (high→low)
    levels: dict  # {0.382: preis, 0.5: preis, ...}
    current_price: float
    nearest_level: float
    nearest_price: float
    distance_pct: float  # (current_price / nearest_price - 1) * 100


def find_swing_points(df: pd.DataFrame, lookback: int = 60) -> tuple:
    """Findet das letzte signifikante Swing-High und Swing-Low im lookback-Fenster.

    Strategie: Wir suchen die jüngste signifikante Swing-Bewegung.
    Wir scannen das Fenster, finden den absoluten High und Low. Wenn der
    absolute High INDEXWEISE NACH dem absoluten Low liegt, dann ist der
    letzte dominante Move ein Aufwärtstrend (Low→High). Sonst Abwärtstrend.

    Edge-Case: Wenn der absolute High und Low sehr nahe beieinander liegen
    (z.B. seitwärts), schauen wir uns die letzten 10 Tage an und bestimmen
    den lokalen Trend.
    """
    if len(df) < lookback:
        lookback = len(df)

    window = df.iloc[-lookback:]
    high_idx = window["High"].idxmax()
    low_idx = window["Low"].idxmin()
    high_price = float(window["High"].max())
    low_price = float(window["Low"].min())

    # Wenn High und Low sehr nahe beieinander (z.B. seitwärts):
    # Wir nutzen die letzten 20% des Fensters, um den Trend zu bestimmen
    if abs(high_idx.value - low_idx.value) < 5 * 24 * 3600 * 1e9:  # < 5 Tage
        recent = window.iloc[-max(5, lookback // 5):]
        if len(recent) >= 2:
            recent_return = (recent["Close"].iloc[-1] / recent["Close"].iloc[0] - 1)
            if recent_return > 0.01:
                trend = "up"
            elif recent_return < -0.01:
                trend = "down"
            else:
                trend = "up"  # Default
            swing_high_idx = window["High"].idxmax()
            swing_low_idx = window["Low"].idxmin()
            return high_price, low_price, swing_high_idx, swing_low_idx, trend

    if high_idx > low_idx:
        # Low zuerst, dann High → Aufwärtstrend (Retracement vom High)
        trend = "up"
        swing_high_idx = high_idx
        swing_low_idx = low_idx
    else:
        # High zuerst, dann Low → Abwärtstrend (Retracement vom Low)
        trend = "down"
        swing_high_idx = high_idx
        swing_low_idx = low_idx

    return high_price, low_price, swing_high_idx, swing_low_idx, trend


def compute_fib_levels(swing_high: float, swing_low: float, trend: str) -> dict:
    """Berechnet Fibonacci-Retracement-Levels.

    Bei 'up'-Trend: Retracement vom High nach unten
        level_preis = swing_high - (swing_high - swing_low) * fib
    Bei 'down'-Trend: Retracement vom Low nach oben
        level_preis = swing_low + (swing_high - swing_low) * fib
    """
    diff = swing_high - swing_low
    if diff == 0:
        return {lvl: swing_low for lvl in FIB_LEVELS}

    if trend == "up":
        # Retracement nach unten von swing_high
        levels = {lvl: swing_high - diff * lvl for lvl in FIB_LEVELS}
    else:
        # Retracement nach oben von swing_low
        levels = {lvl: swing_low + diff * lvl for lvl in FIB_LEVELS}
    return levels


def fib_score(price: float, levels: dict, trend: str) -> tuple:
    """Bewertet wo der aktuelle Kurs relativ zu Fib-Levels steht.

    Returns: (score 0..10, nearest_level, nearest_price, distance_pct)

    Score-Logik:
    - Aufwärtstrend: Kurs nahe 38.2%-61.8% = optimaler Einstieg (10 Pkt)
      → unter 61.8% (also tieferer Retracement): noch zu früh (5 Pkt)
      → zwischen 38.2% und 23.6%: stärkerer Einstieg (8 Pkt)
      → über 38.2% (also näher am High): Trend intakt aber teurer (6-3 Pkt)
    - Abwärtstrend: nicht kaufen → Score 0

    Bei Aufwärtstrend: levels sind absteigend sortiert (0.0=High, 1.0=Low).
    Goldilocks-Zone: 0.382 < price < 0.618 (Retracement zwischen 38.2% und 61.8%).
    """
    if trend == "down":
        return 0.0, 0.5, levels.get(0.5, 0.0), 0.0

    if not levels:
        return 0.0, 0.5, 0.0, 0.0

    # Aufwärtstrend: levels absteigend (0.0=High oben, 1.0=Low unten)
    l_236 = levels.get(0.236, 0)
    l_382 = levels.get(0.382, 0)
    l_500 = levels.get(0.5, 0)
    l_618 = levels.get(0.618, 0)
    l_786 = levels.get(0.786, 0)

    # Nächstes Level finden
    nearest_lvl = min(levels.keys(), key=lambda lvl: abs(levels[lvl] - price))
    nearest_price = levels[nearest_lvl]
    distance_pct = (price / nearest_price - 1) * 100 if nearest_price else 0

    # Scoring — Levels sind im Aufwärtstrend absteigend!
    # Goldilocks: 61.8% ≤ price ≤ 38.2% (also zwischen 0.618- und 0.382-Level)
    if l_618 <= price <= l_382:
        # Goldilocks-Zone (38.2%–61.8% Retracement)
        score = 10.0
    elif price > l_382:
        # Zwischen 23.6% und 38.2% (über 38.2% = näher am High)
        if price <= l_236:
            score = 8.0
        else:
            # Über 23.6% = sehr nahe am High / neue Hochs
            score = 3.0
    else:
        # Unter 61.8% — tieferer Retracement (spekulativer Boden)
        if price >= l_786:
            score = 5.0
        else:
            score = 2.0

    return score, nearest_lvl, nearest_price, distance_pct


def analyze(df: pd.DataFrame, lookback: int = 60) -> FibResult:
    """Hauptfunktion: liefert vollständige Fib-Analyse."""
    if len(df) < 5:
        return FibResult(0, 0, df.index[-1], df.index[-1], "up", {}, 0, 0, 0, 0)

    high, low, hi_idx, lo_idx, trend = find_swing_points(df, lookback)
    levels = compute_fib_levels(high, low, trend)
    current_price = float(df["Close"].iloc[-1])
    score, nearest_lvl, nearest_price, dist_pct = fib_score(current_price, levels, trend)

    return FibResult(
        swing_high=high,
        swing_low=low,
        swing_high_idx=hi_idx,
        swing_low_idx=lo_idx,
        trend=trend,
        levels=levels,
        current_price=current_price,
        nearest_level=nearest_lvl,
        nearest_price=nearest_price,
        distance_pct=dist_pct,
    )