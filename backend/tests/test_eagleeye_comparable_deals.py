"""Tests for EagleEyeScanner.find_comparable_deals — cohort-matching for
coordinated/pooled offerings (Ticket 22 partial)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.eagleeye_scanner import EagleEyeScanner, _score_comparable_deal

scanner = EagleEyeScanner()

TARGET = {
    "id": "jacaranda-2025", "name": "Jacaranda Trace CCRC", "sector": "senior_living",
    "ltv": 65, "dscr": 1.45, "rating": "Baa1",
}


class TestScoreComparableDeal:
    def test_identical_deal_scores_100(self):
        score, n = _score_comparable_deal(TARGET, dict(TARGET))
        assert score == 100.0
        assert n == 3  # ltv, dscr, rating

    def test_no_shared_fields_scores_zero_with_zero_params(self):
        score, n = _score_comparable_deal({"sector": "x"}, {"sector": "x"})
        assert score == 0.0
        assert n == 0

    def test_only_compares_fields_present_on_both(self):
        score, n = _score_comparable_deal(
            {"ltv": 65, "dscr": 1.45},
            {"ltv": 65},  # no dscr on candidate
        )
        assert n == 1  # only ltv compared

    def test_far_apart_values_score_low(self):
        score, n = _score_comparable_deal(
            {"ltv": 65, "dscr": 1.45, "rating": "Baa1"},
            {"ltv": 95, "dscr": 0.7, "rating": "Caa2"},
        )
        assert score < 30


class TestFindComparableDeals:
    CANDIDATES = [
        {"id": "d2", "name": "Similar CCRC A", "sector": "senior_living", "ltv": 63, "dscr": 1.5, "rating": "Baa2"},
        {"id": "d3", "name": "Similar CCRC B", "sector": "senior_living", "ltv": 68, "dscr": 1.4, "rating": "A3"},
        {"id": "d4", "name": "Different Sector Deal", "sector": "industrial", "ltv": 65, "dscr": 1.45, "rating": "Baa1"},
        {"id": "d5", "name": "Weak CCRC", "sector": "senior_living", "ltv": 90, "dscr": 0.9, "rating": "B2"},
    ]

    def test_only_same_sector_considered(self):
        result = scanner.find_comparable_deals(TARGET, candidate_deals=self.CANDIDATES)
        assert result["same_sector_candidates"] == 3  # excludes d4 (industrial)
        matched_ids = {m["deal_id"] for m in result["matches"]}
        assert "d4" not in matched_ids

    def test_weak_comp_excluded_below_min_score(self):
        result = scanner.find_comparable_deals(TARGET, candidate_deals=self.CANDIDATES, min_score=60)
        matched_ids = {m["deal_id"] for m in result["matches"]}
        assert "d5" not in matched_ids

    def test_strong_comps_included_and_ranked(self):
        result = scanner.find_comparable_deals(TARGET, candidate_deals=self.CANDIDATES, min_score=60)
        matched_ids = [m["deal_id"] for m in result["matches"]]
        assert "d2" in matched_ids
        assert "d3" in matched_ids
        # sorted descending by comp_score
        scores = [m["comp_score"] for m in result["matches"]]
        assert scores == sorted(scores, reverse=True)

    def test_excludes_self(self):
        deals_with_self = self.CANDIDATES + [dict(TARGET)]
        result = scanner.find_comparable_deals(TARGET, candidate_deals=deals_with_self)
        matched_ids = {m["deal_id"] for m in result["matches"]}
        assert TARGET["id"] not in matched_ids

    def test_coordinated_offering_viable_requires_at_least_3(self):
        result = scanner.find_comparable_deals(TARGET, candidate_deals=self.CANDIDATES, min_score=60)
        assert result["cohort_size"] == 2
        assert result["coordinated_offering_viable"] is False

    def test_no_candidates_supplied_and_no_supabase_returns_empty_not_fabricated(self, monkeypatch):
        class _UnconfiguredDB:
            configured = False
        monkeypatch.setattr("services.database.db", _UnconfiguredDB())
        result = scanner.find_comparable_deals(TARGET, candidate_deals=None)
        assert result["matches"] == []
        assert result["candidate_source"] == "supabase"
