"""Fundamentale Bewertung: KGV, KBV, FairValue-Marge, Debt/Equity, FCF-Yield, Div-Yield.

Nutzt yfinance via unserer stockscheck_bridge.get_ticker().
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional

try:
    from .stockscheck_bridge import get_ticker, calculateFairValues
except ImportError:
    from .stockscheck_bridge import get_ticker, calculateFairValues


@dataclass
class FundamentalResult:
    symbol: str
    # Preise & Bewertung
    price: Optional[float]
    kgv_trailing: Optional[float]
    kgv_forward: Optional[float]
    kbv: Optional[float]
    # FairValue (verschiedene Modelle, in USD)
    fair_value_graham: Optional[float]
    fair_value_dcf: Optional[float]
    fair_value_peg: Optional[float]
    fair_value_intrinsic: Optional[float]
    fair_value_avg: Optional[float]
    fair_value_margin_pct: Optional[float]  # (avg / price - 1) * 100
    # Health
    debt_to_equity: Optional[float]
    current_ratio: Optional[float]
    free_cashflow: Optional[float]
    fcf_yield_pct: Optional[float]  # FCF / MarketCap * 100
    # Income
    revenue_growth_pct: Optional[float]
    earnings_growth_pct: Optional[float]
    gross_margin_pct: Optional[float]
    operating_margin_pct: Optional[float]
    # Dividende
    dividend_rate: Optional[float]
    dividend_yield_pct: Optional[float]
    payout_ratio_pct: Optional[float]
    # Markt
    market_cap: Optional[float]
    beta: Optional[float]
    fifty_day_avg: Optional[float]
    two_hundred_day_avg: Optional[float]
    # Analysten
    recommendation: Optional[str]
    target_median: Optional[float]
    upside_pct: Optional[float]  # (target / price - 1) * 100
    # Sub-Scores (vom Scorer befüllt)
    sub_score_value: float = 0.0
    sub_score_health: float = 0.0
    sub_score_income: float = 0.0
    sub_score_dividend: float = 0.0
    sub_score_market: float = 0.0
    notes: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def _safe_pct(num, denom):
    """Berechnet Prozentsatz sicher."""
    if num is None or denom is None or denom == 0:
        return None
    return (num / denom) * 100


def _kgv(price, eps):
    if not price or not eps or eps <= 0:
        return None
    return price / eps


def _kbv(price, bv):
    if not price or not bv or bv <= 0:
        return None
    return price / bv


def fetch_fundamentals(symbol: str) -> FundamentalResult:
    """Holt alle Fundamentaldaten von yfinance für ein Symbol."""
    t = get_ticker(symbol)
    info = {}
    try:
        info = t.info
    except Exception as e:
        return FundamentalResult(
            symbol=symbol, price=None, kgv_trailing=None, kgv_forward=None,
            kbv=None, fair_value_graham=None, fair_value_dcf=None,
            fair_value_peg=None, fair_value_intrinsic=None, fair_value_avg=None,
            fair_value_margin_pct=None, debt_to_equity=None, current_ratio=None,
            free_cashflow=None, fcf_yield_pct=None, revenue_growth_pct=None,
            earnings_growth_pct=None, gross_margin_pct=None, operating_margin_pct=None,
            dividend_rate=None, dividend_yield_pct=None, payout_ratio_pct=None,
            market_cap=None, beta=None, fifty_day_avg=None, two_hundred_day_avg=None,
            recommendation=None, target_median=None, upside_pct=None,
            notes=[f"info() failed: {e}"]
        )

    price = info.get("currentPrice") or info.get("regularMarketPrice")
    eps_t = info.get("trailingEps")
    eps_f = info.get("forwardEps")
    bv = info.get("bookValue")

    kgv_t = _kgv(price, eps_t)
    kgv_f = _kgv(price, eps_f)
    kbv = _kbv(price, bv)

    # FairValue
    fair_graham = fair_dcf = fair_peg = fair_intrinsic = None
    fair_avg = None
    fair_margin = None
    try:
        fv_dict = calculateFairValues(info, price)
        fair_graham = fv_dict.get("graham")
        fair_dcf = fv_dict.get("dcf")
        fair_peg = fv_dict.get("peg")
        fair_intrinsic = fv_dict.get("intrinsic")
        fair_avg = fv_dict.get("average")
        if fair_avg and price:
            fair_margin = (fair_avg / price - 1) * 100
    except Exception as e:
        pass

    # Debt/Equity
    de = info.get("debtToEquity")
    if de is not None:
        de = de / 100  # yfinance liefert als Prozent (z.B. 150 = 1.5)

    current_ratio = info.get("currentRatio")
    fcf = info.get("freeCashflow")
    market_cap = info.get("marketCap")
    fcf_yield = _safe_pct(fcf, market_cap) if fcf and market_cap else None

    rev_growth = info.get("revenueGrowth")
    rev_growth_pct = rev_growth * 100 if rev_growth is not None else None
    earn_growth = info.get("earningsGrowth")
    earn_growth_pct = earn_growth * 100 if earn_growth is not None else None

    gm = info.get("grossMargins")
    gm_pct = gm * 100 if gm is not None else None
    om = info.get("operatingMargins")
    om_pct = om * 100 if om is not None else None

    div_rate = info.get("dividendRate")
    # yfinance liefert dividendYield BEREITS in Prozent (z.B. 0.35 = 0.35%),
    # während payoutRatio als Bruch kommt (0.12 = 12%). Daher KEIN *100.
    div_yield = info.get("dividendYield")
    div_yield_pct = div_yield if div_yield is not None else None
    payout = info.get("payoutRatio")
    payout_pct = payout * 100 if payout is not None else None

    beta = info.get("beta")
    ma50 = info.get("fiftyDayAverage")
    ma200 = info.get("twoHundredDayAverage")
    recommendation = info.get("recommendationKey")
    target = info.get("targetMedianPrice")
    upside = None
    if target and price:
        upside = (target / price - 1) * 100

    return FundamentalResult(
        symbol=symbol,
        price=price,
        kgv_trailing=kgv_t,
        kgv_forward=kgv_f,
        kbv=kbv,
        fair_value_graham=fair_graham,
        fair_value_dcf=fair_dcf,
        fair_value_peg=fair_peg,
        fair_value_intrinsic=fair_intrinsic,
        fair_value_avg=fair_avg,
        fair_value_margin_pct=fair_margin,
        debt_to_equity=de,
        current_ratio=current_ratio,
        free_cashflow=fcf,
        fcf_yield_pct=fcf_yield,
        revenue_growth_pct=rev_growth_pct,
        earnings_growth_pct=earn_growth_pct,
        gross_margin_pct=gm_pct,
        operating_margin_pct=om_pct,
        dividend_rate=div_rate,
        dividend_yield_pct=div_yield_pct,
        payout_ratio_pct=payout_pct,
        market_cap=market_cap,
        beta=beta,
        fifty_day_avg=ma50,
        two_hundred_day_avg=ma200,
        recommendation=recommendation,
        target_median=target,
        upside_pct=upside,
    )


def value_score(f: FundamentalResult) -> float:
    """Bewertet Value-Subscore: KGV + KBV + FairValue-Marge. Max 35 Punkte.

    KGV (10): <15=10, 15-20=8, 20-25=5, 25-35=2, >35=0
    KBV (10): <1.5=10, 1.5-3=8, 3-5=5, 5-10=2, >10=0
    FairValue-Marge (15): linear skaliert; +20%=15, +10%=12, 0%=7, -10%=3, -20%=0
    """
    score = 0.0

    # KGV
    if f.kgv_trailing is None or f.kgv_trailing <= 0:
        kgv_pts = 0
    elif f.kgv_trailing < 15:
        kgv_pts = 10
    elif f.kgv_trailing < 20:
        kgv_pts = 8
    elif f.kgv_trailing < 25:
        kgv_pts = 5
    elif f.kgv_trailing < 35:
        kgv_pts = 2
    else:
        kgv_pts = 0
    score += kgv_pts

    # KBV
    if f.kbv is None or f.kbv <= 0:
        kbv_pts = 0
    elif f.kbv < 1.5:
        kbv_pts = 10
    elif f.kbv < 3:
        kbv_pts = 8
    elif f.kbv < 5:
        kbv_pts = 5
    elif f.kbv < 10:
        kbv_pts = 2
    else:
        kbv_pts = 0
    score += kbv_pts

    # FairValue-Marge
    if f.fair_value_margin_pct is None:
        fv_pts = 0
    else:
        m = f.fair_value_margin_pct
        if m >= 20:
            fv_pts = 15
        elif m >= 10:
            fv_pts = 12
        elif m >= 0:
            fv_pts = 7
        elif m >= -10:
            fv_pts = 3
        else:
            fv_pts = 0
    score += fv_pts

    return round(score, 2)


def health_score(f: FundamentalResult) -> float:
    """Bewertet Health-Subscore: Debt/Equity + FCF-Yield. Max 10 Punkte.

    Net-Cash oder D/E<0.5 = 5 Pkt, 0.5-1.0 = 4, 1-2 = 2, >2 = 0
    FCF-Yield >5% = 5 Pkt, 3-5% = 4, 1-3% = 2, <1% = 0
    """
    score = 0.0

    # Debt/Equity
    if f.debt_to_equity is None:
        de_pts = 0
    elif f.debt_to_equity < 0.5:
        de_pts = 5
    elif f.debt_to_equity < 1.0:
        de_pts = 4
    elif f.debt_to_equity < 2.0:
        de_pts = 2
    else:
        de_pts = 0
    score += de_pts

    # FCF-Yield
    if f.fcf_yield_pct is None:
        fcf_pts = 0
    elif f.fcf_yield_pct > 5:
        fcf_pts = 5
    elif f.fcf_yield_pct > 3:
        fcf_pts = 4
    elif f.fcf_yield_pct > 1:
        fcf_pts = 2
    else:
        fcf_pts = 0
    score += fcf_pts

    return round(score, 2)


def income_score(f: FundamentalResult) -> float:
    """Bewertet Wachstum-Subscore: Revenue/Earnings Growth. Max 0 (Bonus, separat)."""
    return 0.0  # Wir nutzen das nicht direkt; Wachstum fliesst via Empfehlung ein


def dividend_score(f: FundamentalResult) -> float:
    """Dividenden-Subscore (Bonus, max 3 Pkt)."""
    if f.dividend_yield_pct is None or f.dividend_yield_pct <= 0:
        return 0.0
    if f.dividend_yield_pct >= 3:
        return 3.0
    if f.dividend_yield_pct >= 2:
        return 2.0
    if f.dividend_yield_pct >= 1:
        return 1.0
    return 0.0


def analyst_bonus(f: FundamentalResult) -> float:
    """Analysten-Bonus (max 3 Pkt) wenn Rating buy/strong_buy ODER hohes Upside."""
    if f.recommendation in ("strongBuy", "strong_buy"):
        return 3.0
    if f.recommendation in ("buy",):
        return 2.0
    # Hold + trotzdem Upside >20% → moderate bullishes Signal
    if f.upside_pct is not None and f.upside_pct >= 25 and f.recommendation not in ("sell", "strongSell", "strong_sell"):
        return 1.0
    return 0.0


def score_fundamentals(f: FundamentalResult) -> None:
    """Befüllt alle Sub-Scores in-place."""
    f.sub_score_value = value_score(f)
    f.sub_score_health = health_score(f)
    f.sub_score_dividend = dividend_score(f)
    # Analyst-Bonus wird im Scorer addiert (Bonus-Topf)