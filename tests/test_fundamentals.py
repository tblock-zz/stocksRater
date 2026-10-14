"""Tests für Fundamental-Scoring-Funktionen (deterministisch)."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from stockscheck.fundamentals import (
    FundamentalResult, value_score, health_score, dividend_score, analyst_bonus
)


def make_fund(**overrides):
    defaults = dict(
        symbol="X", price=100.0, kgv_trailing=20.0, kgv_forward=18.0, kbv=2.0,
        fair_value_graham=120, fair_value_dcf=110, fair_value_peg=130,
        fair_value_intrinsic=115, fair_value_avg=117.5,
        fair_value_margin_pct=17.5,
        debt_to_equity=0.5, current_ratio=2.0, free_cashflow=5e9, fcf_yield_pct=5.0,
        revenue_growth_pct=10.0, earnings_growth_pct=12.0,
        gross_margin_pct=40.0, operating_margin_pct=20.0,
        dividend_rate=2.0, dividend_yield_pct=2.0, payout_ratio_pct=40.0,
        market_cap=1e11, beta=1.0, fifty_day_avg=99, two_hundred_day_avg=95,
        recommendation="buy", target_median=120, upside_pct=20.0,
        sub_score_value=0, sub_score_health=0, sub_score_income=0,
        sub_score_dividend=0, notes=[],
    )
    defaults.update(overrides)
    return FundamentalResult(**defaults)


def test_value_score_kgv_under_15():
    f = make_fund(kgv_trailing=12, kbv=1.0, fair_value_margin_pct=25)
    # KGV=10, KBV=10, FV-Marge 25% → 15
    # Total: 10+10+15 = 35
    score = value_score(f)
    assert score == 35.0, f"Expected 35, got {score}"


def test_value_score_high_kgv_zero():
    f = make_fund(kgv_trailing=50, kbv=15, fair_value_margin_pct=-30)
    # KGV=0, KBV=0, FV=-30% → 0
    score = value_score(f)
    assert score == 0.0, f"Expected 0, got {score}"


def test_value_score_mid():
    f = make_fund(kgv_trailing=22, kbv=4, fair_value_margin_pct=5)
    # KGV=5, KBV=5, FV=7 → 17
    score = value_score(f)
    assert score == 17.0, f"Expected 17, got {score}"


def test_health_score_strong():
    f = make_fund(debt_to_equity=0.3, fcf_yield_pct=6)
    # D/E<0.5 → 5, FCF>5 → 5
    assert health_score(f) == 10.0


def test_health_score_weak():
    f = make_fund(debt_to_equity=3.0, fcf_yield_pct=0.5)
    # D/E>2 → 0, FCF<1 → 0
    assert health_score(f) == 0.0


def test_health_score_no_data():
    f = make_fund(debt_to_equity=None, fcf_yield_pct=None)
    assert health_score(f) == 0.0


def test_dividend_score_tiers():
    assert dividend_score(make_fund(dividend_yield_pct=4.0)) == 3.0
    assert dividend_score(make_fund(dividend_yield_pct=2.5)) == 2.0
    assert dividend_score(make_fund(dividend_yield_pct=1.5)) == 1.0
    assert dividend_score(make_fund(dividend_yield_pct=0.5)) == 0.0
    assert dividend_score(make_fund(dividend_yield_pct=None)) == 0.0
    assert dividend_score(make_fund(dividend_yield_pct=0)) == 0.0


def test_analyst_bonus():
    assert analyst_bonus(make_fund(recommendation="strongBuy")) == 3.0
    assert analyst_bonus(make_fund(recommendation="strong_buy")) == 3.0
    assert analyst_bonus(make_fund(recommendation="buy")) == 2.0
    assert analyst_bonus(make_fund(recommendation="hold")) == 0.0
    # Hold + hohes Upside (>25%) → moderater Bonus
    assert analyst_bonus(make_fund(recommendation=None, upside_pct=25)) == 1.0
    # Hold + niedriges Upside → kein Bonus
    assert analyst_bonus(make_fund(recommendation=None, upside_pct=5)) == 0.0


if __name__ == "__main__":
    test_value_score_kgv_under_15(); print("✓ value_under_15")
    test_value_score_high_kgv_zero(); print("✓ value_high_kgv_zero")
    test_value_score_mid(); print("✓ value_mid")
    test_health_score_strong(); print("✓ health_strong")
    test_health_score_weak(); print("✓ health_weak")
    test_health_score_no_data(); print("✓ health_no_data")
    test_dividend_score_tiers(); print("✓ dividend_tiers")
    test_analyst_bonus(); print("✓ analyst_bonus")
    print("\nAll fundamental tests passed.")