"""Tests for IntelligenceEngine.size_ma_acquisition — Ticket 11: the balance
check must never push senior leverage past the sector's real ceiling; any
unfunded shortfall is a real equity gap, not more bond capacity."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.intelligence_engine import IntelligenceEngine

engine = IntelligenceEngine()


class TestLeverageCeilingRespected:
    def test_deal_with_enough_debt_headroom_has_no_equity_gap(self):
        """With generous sponsor equity (thin bond_needed relative to the
        sector's senior ceiling), the leftover debt headroom fully absorbs
        reserves/cost-of-issuance and no equity gap results."""
        result = engine.size_ma_acquisition({
            "ebitda": 5_000_000, "sector": "business_services",
            "acquisition_multiple": 4.5, "sponsor_equity_pct": 0.50,
        })
        su = result["sources_and_uses"]
        assert su["has_equity_gap"] is False
        assert su["equity_gap_usd"] == 0

    def test_thin_equity_normal_multiple_can_still_surface_a_small_real_gap(self):
        """Reserves + cost-of-issuance were never included in the original
        bond_needed formula — only bolted on afterward via unconditional
        over-leverage. With thin sponsor equity, senior debt is sized close
        to the ceiling already, leaving little headroom to absorb them, so
        even an otherwise-ordinary deal can show a real (if small) gap."""
        result = engine.size_ma_acquisition({
            "ebitda": 5_000_000, "sector": "business_services",
            "acquisition_multiple": 4.5, "sponsor_equity_pct": 0.30,
        })
        cap = result["capital_structure"]
        assert cap["senior_leverage"] <= cap["max_senior_leverage"] + 0.01

    def test_thin_equity_high_uses_surfaces_real_equity_gap(self):
        result = engine.size_ma_acquisition({
            "ebitda": 5_000_000, "sector": "business_services",
            "acquisition_multiple": 6.0, "sponsor_equity_pct": 0.10,
            "transaction_expenses": 3_000_000, "working_capital_cushion": 5_000_000,
        })
        su = result["sources_and_uses"]
        cap = result["capital_structure"]
        assert su["has_equity_gap"] is True
        assert su["equity_gap_usd"] > 0
        # The real fix: senior leverage never exceeds the sector ceiling
        assert cap["senior_leverage"] <= cap["max_senior_leverage"] + 0.01

    def test_gap_case_sources_do_not_equal_uses(self):
        """When a real equity gap exists, sources_and_uses is honestly
        unbalanced — previously this was hidden by over-levering to force
        balance regardless of the leverage ceiling."""
        result = engine.size_ma_acquisition({
            "ebitda": 5_000_000, "sector": "business_services",
            "acquisition_multiple": 6.0, "sponsor_equity_pct": 0.10,
            "transaction_expenses": 3_000_000, "working_capital_cushion": 5_000_000,
        })
        su = result["sources_and_uses"]
        assert su["balanced"] is False
        gap_accounted = su["uses"]["total"] - su["sources"]["total"]
        assert abs(gap_accounted - su["equity_gap_usd"]) < 1

    def test_total_leverage_reflects_final_bond_amount(self):
        result = engine.size_ma_acquisition({
            "ebitda": 5_000_000, "sector": "business_services",
            "acquisition_multiple": 6.0, "sponsor_equity_pct": 0.10,
            "transaction_expenses": 3_000_000, "working_capital_cushion": 5_000_000,
        })
        cap = result["capital_structure"]
        assert cap["total_leverage"] <= cap["max_total_leverage"] + 0.01
