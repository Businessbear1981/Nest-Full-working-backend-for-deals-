"""Tests for SuretyScoutAgent — premium base and units."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.surety_scout import surety_scout


class TestSuretyPremiumBase:
    """Ticket 7: contract-surety products (performance/payment/bid/maintenance
    bonds) must price off construction contract value, not the full bond
    face — pricing a performance bond against the whole raise (which also
    funds land, soft costs, fees, and reserves) overstated the premium by
    roughly 1/DEFAULT_CONTRACT_VALUE_PCT_OF_FACE, ~2.5x in the case tested.
    """

    def test_performance_bond_prices_off_contract_value_not_bond_face(self):
        deal = {
            "bond_face_usd": 100_000_000,
            "construction_contract_value_usd": 40_000_000,
            "rating_target": "BBB",
            "asset_type": "multifamily",
            "state": "NY",
            "duration_years": 3,
            "dscr": 1.5,
            "ltv_pct": 65,
        }
        result = surety_scout.calculate_premium(deal)
        perf = result["options"]["performance_bond"]
        assert perf["priced_off"] == "construction_contract_value"
        assert perf["base_amount_usd"] == 40_000_000
        # annual premium must scale off the 40M contract, not the 100M bond face
        assert perf["annual_premium_usd"] < perf["adjusted_rate_bps"] / 10000 * 100_000_000

    def test_financial_guarantee_products_still_price_off_bond_face(self):
        deal = {
            "bond_face_usd": 100_000_000,
            "construction_contract_value_usd": 40_000_000,
            "rating_target": "BBB",
            "duration_years": 3,
        }
        result = surety_scout.calculate_premium(deal)
        for product in ("cash_surety_sbloc", "lc", "parametric"):
            opt = result["options"][product]
            assert opt["priced_off"] == "bond_face"
            assert opt["base_amount_usd"] == 100_000_000

    def test_missing_contract_value_falls_back_to_defensible_fraction_of_face(self):
        """No explicit contract value supplied — must not silently default
        to the full bond face (the original bug)."""
        deal = {"bond_face_usd": 100_000_000, "rating_target": "BBB", "duration_years": 3}
        result = surety_scout.calculate_premium(deal)
        perf = result["options"]["performance_bond"]
        assert perf["base_amount_usd"] < 100_000_000
        assert perf["base_amount_usd"] == round(100_000_000 * 0.65)

    def test_overstatement_vs_old_bond_face_basis_is_real(self):
        """Regression for the ~2.5x overstatement: computing the old way
        (bond_face as base) must produce a materially larger premium than
        the fixed contract-value basis."""
        deal = {
            "bond_face_usd": 100_000_000,
            "construction_contract_value_usd": 40_000_000,
            "rating_target": "BBB_minus",
            "duration_years": 3,
        }
        result = surety_scout.calculate_premium(deal)
        perf = result["options"]["performance_bond"]
        old_way_annual = perf["adjusted_rate_bps"] / 10000 * 100_000_000
        ratio = old_way_annual / perf["annual_premium_usd"]
        assert abs(ratio - 100_000_000 / 40_000_000) < 0.01
