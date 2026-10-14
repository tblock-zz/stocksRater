"""Scoring-Engine: Kombiniert Technical + Fundamental + Bonus → Score 0-100, Grade A-F."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

try:
    from .indicators import TechnicalResult, score_technical
    from .fundamentals import FundamentalResult, score_fundamentals, analyst_bonus
except ImportError:
    from .indicators import TechnicalResult, score_technical
    from .fundamentals import FundamentalResult, score_fundamentals, analyst_bonus


@dataclass
class StockRating:
    symbol: str
    technical: TechnicalResult
    fundamental: FundamentalResult
    # Sub-Scores (zur Transparenz)
    trend_pts: float = 0.0
    rsi_pts: float = 0.0
    macd_pts: float = 0.0
    stoch_pts: float = 0.0
    fib_pts: float = 0.0
    technical_total: float = 0.0  # /55 max
    kgv_pts: float = 0.0
    kbv_pts: float = 0.0
    fv_pts: float = 0.0
    health_pts: float = 0.0
    value_total: float = 0.0  # /45 max
    div_bonus: float = 0.0
    analyst_bonus: float = 0.0
    total_score: float = 0.0   # /100 max
    grade: str = "F"
    action: str = ""  # "STRONG BUY", "BUY", "HOLD", "AVOID", "SELL"
    reasons: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "total_score": self.total_score,
            "grade": self.grade,
            "action": self.action,
            "trend_pts": self.trend_pts,
            "rsi_pts": self.rsi_pts,
            "macd_pts": self.macd_pts,
            "stoch_pts": self.stoch_pts,
            "fib_pts": self.fib_pts,
            "technical_total": self.technical_total,
            "kgv_pts": self.kgv_pts,
            "kbv_pts": self.kbv_pts,
            "fv_pts": self.fv_pts,
            "health_pts": self.health_pts,
            "value_total": self.value_total,
            "div_bonus": self.div_bonus,
            "analyst_bonus": self.analyst_bonus,
            "reasons": self.reasons,
            "fundamentals": self.fundamental.to_dict(),
            "technical_summary": {
                "last_price": self.technical.last_price,
                "trend": self.technical.trend,
                "sma50": self.technical.sma50,
                "sma200": self.technical.sma200,
                "rsi": self.technical.rsi,
                "macd_trend": self.technical.macd_trend,
                "stoch_signal": self.technical.stoch_signal,
                "fib_trend": self.technical.fib.trend,
                "fib_nearest_level": self.technical.fib.nearest_level,
            },
        }


def score_to_grade(score: float) -> tuple:
    """Mappt Score → Grade + Action."""
    if score >= 75:
        return "A", "STRONG BUY"
    if score >= 60:
        return "B", "BUY"
    if score >= 45:
        return "C", "HOLD"
    if score >= 30:
        return "D", "AVOID"
    return "F", "SELL"


def build_rating(tech: TechnicalResult, fund: FundamentalResult) -> StockRating:
    """Baut eine vollständige Bewertung aus Technical + Fundamental.

    Sub-Scores werden IMMER aus den Rohwerten neu berechnet.
    """
    # Sub-Scores werden immer aus den Rohwerten neu berechnet — single source of truth.
    # (Test-Mocks, die sub_score_* vorab setzen, werden bewusst überschrieben —
    # siehe Pitfall #4 in SKILL.md.)
    score_technical(tech)
    score_fundamentals(fund)

    rating = StockRating(symbol=tech.symbol, technical=tech, fundamental=fund)

    # Technical (max 55)
    rating.trend_pts = tech.sub_score_trend
    rating.rsi_pts = tech.sub_score_rsi
    rating.macd_pts = tech.sub_score_macd
    rating.stoch_pts = tech.sub_score_stoch
    rating.fib_pts = tech.sub_score_fib
    rating.technical_total = sum([
        tech.sub_score_trend, tech.sub_score_rsi, tech.sub_score_macd,
        tech.sub_score_stoch, tech.sub_score_fib,
    ])

    # Value (max 45: KGV 10 + KBV 10 + FairValue 15 + Health 10)
    # Wir mappen die Value-Subscores auf die einzelnen Felder für Transparenz
    value_score_total = fund.sub_score_value  # = KGV + KBV + FV
    # Recompute split: KGV=10, KBV=10, FV=15 (value_score returned sum)
    if fund.kgv_trailing and fund.kgv_trailing > 0:
        kgv = fund.kgv_trailing
        if kgv < 15: rating.kgv_pts = 10
        elif kgv < 20: rating.kgv_pts = 8
        elif kgv < 25: rating.kgv_pts = 5
        elif kgv < 35: rating.kgv_pts = 2
        else: rating.kgv_pts = 0
    if fund.kbv and fund.kbv > 0:
        kbv = fund.kbv
        if kbv < 1.5: rating.kbv_pts = 10
        elif kbv < 3: rating.kbv_pts = 8
        elif kbv < 5: rating.kbv_pts = 5
        elif kbv < 10: rating.kbv_pts = 2
        else: rating.kbv_pts = 0
    rating.fv_pts = max(0, value_score_total - rating.kgv_pts - rating.kbv_pts)

    rating.health_pts = fund.sub_score_health
    rating.value_total = rating.kgv_pts + rating.kbv_pts + rating.fv_pts + rating.health_pts

    # Bonus (max 8)
    rating.div_bonus = fund.sub_score_dividend
    rating.analyst_bonus = analyst_bonus(fund)

    # Total
    rating.total_score = (
        rating.technical_total
        + rating.value_total
        + rating.div_bonus
        + rating.analyst_bonus
    )

    rating.grade, rating.action = score_to_grade(rating.total_score)

    # Reasons (Top-3 starke / schwache Signale)
    reasons = []
    if tech.sub_score_trend >= 12:
        reasons.append(f"Starker Aufwärtstrend (SMA50 über SMA200, {tech.sma50_vs_sma200_pct:+.1f}%)")
    elif tech.sub_score_trend <= 2:
        reasons.append(f"Abwärtstrend (SMA50 unter SMA200, {tech.sma50_vs_sma200_pct:+.1f}%)")
    if tech.sub_score_rsi >= 9:
        reasons.append(f"RSI überverkauft ({tech.rsi:.0f}) — Einstiegs-Chance")
    elif tech.sub_score_rsi == 0 and tech.rsi > 70:
        reasons.append(f"RSI überkauft ({tech.rsi:.0f}) — Vorsicht")
    if tech.sub_score_fib >= 10:
        reasons.append(f"Kurs in Fib-Goldilocks-Zone (38.2–61.8%)")
    if rating.fv_pts >= 12:
        reasons.append(f"FairValue-Marge positiv: Unterbewertet ({fund.fair_value_margin_pct:+.1f}%)")
    elif rating.fv_pts <= 3 and fund.fair_value_margin_pct is not None and fund.fair_value_margin_pct < -10:
        reasons.append(f"FairValue-Marge negativ: Überbewertet ({fund.fair_value_margin_pct:+.1f}%)")
    if rating.health_pts >= 8:
        reasons.append(f"Starke Bilanz (D/E={fund.debt_to_equity}, FCF-Yield={fund.fcf_yield_pct:.1f}%)")
    elif rating.health_pts <= 2:
        reasons.append(f"Schwache Bilanz (D/E={fund.debt_to_equity})")
    if rating.div_bonus > 0:
        reasons.append(f"Dividende {fund.dividend_yield_pct:.1f}%")
    if rating.analyst_bonus > 0:
        reasons.append(f"Analysten-Rating: {fund.recommendation}")

    rating.reasons = reasons
    return rating


def grade_distribution(ratings: List[StockRating]) -> dict:
    """Verteilung der Grades über mehrere Ratings."""
    dist = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for r in ratings:
        dist[r.grade] = dist.get(r.grade, 0) + 1
    return dist