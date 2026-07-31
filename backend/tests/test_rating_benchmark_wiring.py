"""Tests for Ticket 6 — architect/maxwell_engine/sentinel actually consuming
services/rating_benchmarks.py's real S&P/Moody's benchmark data, instead of
each independently inventing its own DSCR/LTV/leverage cutoffs.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engines.maxwell_engine import score_deal as maxwell_score_deal
from engines.architect import generate_candidates
from agents.sentinel import sentinel

STRONG_DEAL = {
    "id": "strong-1",
    "stabilized_noi_usd": 20_000_000,
    "a_tranche_usd": 60_000_000,
    "b_tranche_usd": 0,
    "a_coupon_pct": 5.5,
    "total_project_cost_usd": 100_000_000,
    "appraised_value_usd": 120_000_000,
    "sponsor_equity_usd": 40_000_000,
}

MODERATE_DEAL = {
    "id": "moderate-1",
    "stabilized_noi_usd": 10_000_000,
    "a_tranche_usd": 80_000_000,
    "b_tranche_usd": 5_000_000,
    "a_coupon_pct": 6.5,
    "total_project_cost_usd": 100_000_000,
    "appraised_value_usd": 105_000_000,
    "sponsor_equity_usd": 20_000_000,
}

WEAK_DEAL = {
    "id": "weak-1",
    "stabilized_noi_usd": 4_000_000,
    "a_tranche_usd": 90_000_000,
    "b_tranche_usd": 10_000_000,
    "a_coupon_pct": 8.0,
    "total_project_cost_usd": 100_000_000,
    "appraised_value_usd": 95_000_000,
    "sponsor_equity_usd": 5_000_000,
}


class TestMaxwellEngineBenchmarkWiring:
    def test_output_includes_sp_financial_risk_crosscheck(self):
        result = maxwell_score_deal(STRONG_DEAL)
        assert "sp_financial_risk" in result
        assert "combined_category" in result["sp_financial_risk"]

    def test_three_different_deals_produce_three_different_ratings(self):
        ratings = {
            maxwell_score_deal(STRONG_DEAL)["indicative_rating"],
            maxwell_score_deal(MODERATE_DEAL)["indicative_rating"],
            maxwell_score_deal(WEAK_DEAL)["indicative_rating"],
        }
        assert len(ratings) == 3, f"expected 3 distinct ratings, got {ratings}"

    def test_dscr_score_uses_real_structuring_criteria_floors(self):
        from engines.maxwell_engine import _dscr_to_score
        from services.rating_benchmarks import STRUCTURING_CRITERIA
        # Just above the real BBB floor must score better than just below it
        bbb_floor = STRUCTURING_CRITERIA["dscr_by_rating"]["BBB"]["min"]
        assert _dscr_to_score(bbb_floor + 0.01) < _dscr_to_score(bbb_floor - 0.01)


class TestSentinelBenchmarkWiring:
    def test_credit_risk_uses_real_dscr_floor_language(self):
        from agents.sentinel import _DSCR_IG_FLOOR
        result = sentinel.score_credit_risk({"dscr": _DSCR_IG_FLOOR - 0.1, "ltv": 60, "debt_to_ebitda": 3.0})
        assert any(str(_DSCR_IG_FLOOR) in f for f in result["factors"])

    def test_three_different_deals_produce_three_different_credit_scores(self):
        scores = {
            sentinel.score_credit_risk({"dscr": 2.2, "ltv": 50, "debt_to_ebitda": 3.0})["score"],
            sentinel.score_credit_risk({"dscr": 1.35, "ltv": 68, "debt_to_ebitda": 5.0})["score"],
            sentinel.score_credit_risk({"dscr": 1.0, "ltv": 82, "debt_to_ebitda": 7.0})["score"],
        }
        assert len(scores) == 3, f"expected 3 distinct scores, got {scores}"


class TestArchitectBenchmarkWiring:
    def test_output_includes_real_structuring_targets(self):
        result = generate_candidates(STRONG_DEAL, target_rating="A")
        assert "structuring_targets" in result
        assert result["structuring_targets"]["min_dscr"] == 1.50  # real A-grade floor
        assert "meets_min_dscr_for_target" in result

    def test_weak_deal_fails_min_dscr_check_for_high_target(self):
        result = generate_candidates(WEAK_DEAL, target_rating="A")
        assert result["meets_min_dscr_for_target"] is False
