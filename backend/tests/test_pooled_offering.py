"""Tests for EagleEyeScanner.structure_pooled_offering -- coordinated
multi-deal offering structuring ("Rico" in the agent registry) on top of
find_comparable_deals()'s cohort matching."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.eagleeye_scanner import EagleEyeScanner

scanner = EagleEyeScanner()

DEALS = [
    {"id": "d1", "name": "CCRC A", "bond_face": 60_000_000, "dscr": 1.5, "ltv": 65, "rating": "Baa1", "noi": 6_000_000},
    {"id": "d2", "name": "CCRC B", "bond_face": 40_000_000, "dscr": 1.4, "ltv": 68, "rating": "Baa2", "noi": 3_500_000},
    {"id": "d3", "name": "CCRC C", "bond_face": 50_000_000, "dscr": 1.55, "ltv": 63, "rating": "A3", "noi": 5_200_000},
]


class TestPoolSizeFloor:
    def test_fewer_than_three_deals_not_viable(self):
        result = scanner.structure_pooled_offering(DEALS[:2])
        assert result["viable"] is False

    def test_no_par_data_not_viable(self):
        result = scanner.structure_pooled_offering([
            {"id": "a", "name": "A"}, {"id": "b", "name": "B"}, {"id": "c", "name": "C"},
        ])
        assert result["viable"] is False


class TestAggregateMath:
    def test_total_par_is_real_sum(self):
        result = scanner.structure_pooled_offering(DEALS)
        assert result["total_par_usd"] == 150_000_000

    def test_weighted_dscr_is_par_weighted_not_simple_average(self):
        result = scanner.structure_pooled_offering(DEALS)
        # simple average would be (1.5+1.4+1.55)/3 = 1.483; par-weighted differs
        simple_avg = round((1.5 + 1.4 + 1.55) / 3, 3)
        assert result["weighted_dscr"] != simple_avg
        expected = round((1.5 * 60e6 + 1.4 * 40e6 + 1.55 * 50e6) / 150e6, 3)
        assert result["weighted_dscr"] == expected

    def test_blended_rating_is_weakest_link_not_average(self):
        result = scanner.structure_pooled_offering(DEALS)
        # Baa1, Baa2, A3 -> weakest is Baa2 (A3 is stronger than Baa1/Baa2)
        assert result["blended_rating"] == "Baa2"

    def test_missing_leverage_field_returns_none_not_fabricated(self):
        result = scanner.structure_pooled_offering(DEALS)
        assert result["weighted_debt_to_ebitda"] is None


class TestFeeEconomicsNoConflictOfInterest:
    """Must not repeat Ticket 16's PhaseBondEngine bug -- pooling cannot
    justify itself by charging more per dollar than a standalone deal."""

    def test_pooled_fee_equals_sum_of_separate_fees(self):
        result = scanner.structure_pooled_offering(DEALS)
        fees = result["fee_economics"]
        assert fees["pooled_arrangement_fee_usd"] == fees["separate_arrangement_fees_usd"]

    def test_fee_rate_matches_real_platform_convention(self):
        result = scanner.structure_pooled_offering(DEALS)
        assert result["fee_economics"]["fee_rate_pct"] == 2.25

    def test_note_does_not_frame_pooling_as_more_fee_income(self):
        result = scanner.structure_pooled_offering(DEALS)
        note = result["fee_economics"]["note"].lower()
        assert "more fee" not in note
        assert "2-3x" not in note


class TestSharedEnhancement:
    def test_computed_when_noi_and_dscr_present(self):
        result = scanner.structure_pooled_offering(DEALS)
        assert result["shared_enhancement"] is not None
        assert result["shared_enhancement"]["premium_usd"] > 0

    def test_none_when_no_debt_service_data_available(self):
        deals_no_noi = [
            {"id": "a", "name": "A", "bond_face": 10_000_000},
            {"id": "b", "name": "B", "bond_face": 10_000_000},
            {"id": "c", "name": "C", "bond_face": 10_000_000},
        ]
        result = scanner.structure_pooled_offering(deals_no_noi)
        assert result["shared_enhancement"] is None

    def test_uses_explicit_annual_debt_service_when_present(self):
        deals = [
            {"id": "a", "name": "A", "bond_face": 10_000_000, "annual_debt_service": 700_000},
            {"id": "b", "name": "B", "bond_face": 10_000_000, "annual_debt_service": 650_000},
            {"id": "c", "name": "C", "bond_face": 10_000_000, "annual_debt_service": 720_000},
        ]
        result = scanner.structure_pooled_offering(deals)
        assert result["shared_enhancement"]["total_debt_service"] == 2_070_000
