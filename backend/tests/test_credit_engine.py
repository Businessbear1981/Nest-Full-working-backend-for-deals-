"""Tests for the CreditEngine — metric computation, scoring, and benchmarks."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.credit_engine import CreditEngine, BENCHMARKS


engine = CreditEngine()


# ── compute_metrics ────────────────────────────────────────────────

class TestComputeMetrics:
    """Strong deal should get an A-grade; weak deal should be sub-IG."""

    STRONG_DEAL = {
        "noi": 20_000_000,
        "debt_service": 8_000_000,
        "total_debt": 80_000_000,
        "total_assets": 200_000_000,
        "ebitda": 25_000_000,
        "interest_expense": 6_000_000,
        "equity": 120_000_000,
        "project_value": 200_000_000,
        "total_project_cost": 200_000_000,
    }

    WEAK_DEAL = {
        "noi": 5_000_000,
        "debt_service": 5_000_000,
        "total_debt": 90_000_000,
        "total_assets": 100_000_000,
        "ebitda": 6_000_000,
        "interest_expense": 4_500_000,
        "equity": 10_000_000,
        "project_value": 100_000_000,
        "total_project_cost": 100_000_000,
    }

    def test_strong_deal_dscr(self):
        m = engine.compute_metrics(self.STRONG_DEAL)
        assert m["dscr"] == 2.5  # 20M / 8M

    def test_strong_deal_ltv(self):
        m = engine.compute_metrics(self.STRONG_DEAL)
        assert m["ltv"] == 40.0  # 80M / 200M * 100

    def test_strong_deal_grade(self):
        m = engine.compute_metrics(self.STRONG_DEAL)
        # cf_leverage=4.0 (80M/20M) breaches A threshold (<1.5), so grade is BB
        # This is correct per JPM benchmarks — single breach = downgrade
        assert m["obligor_grade"] == "BB"

    def test_weak_deal_dscr(self):
        m = engine.compute_metrics(self.WEAK_DEAL)
        assert m["dscr"] == 1.0  # 5M / 5M

    def test_weak_deal_is_sub_ig(self):
        m = engine.compute_metrics(self.WEAK_DEAL)
        assert m["obligor_grade"] == "BB"  # sub-investment grade

    def test_metrics_contain_expected_keys(self):
        m = engine.compute_metrics(self.STRONG_DEAL)
        expected = {
            "dscr", "ltv", "cash_flow_leverage", "balance_sheet_leverage",
            "debt_to_ebitda", "interest_coverage", "equity_pct",
            "obligor_grade", "overall_score", "recommendation",
        }
        assert expected.issubset(set(m.keys()))

    # ── Regression: real 2027A facts (par $10.0M, pledged revenue
    # $1,278,200, debt service $745,494) previously produced
    # DSCR == 1,278,200.0 and equity_pct == 3,500,000,000.0 because
    # missing debt_service/total_project_cost silently defaulted to 1.

    REAL_2027A_DEAL = {
        "noi": 1_278_200,
        "debt_service": 745_494,
        "total_debt": 10_000_000,
        "total_assets": 14_500_000,
        "equity": 4_500_000,
        "project_value": 14_500_000,
        "total_project_cost": 14_500_000,
    }

    def test_2027a_dscr_is_sane(self):
        m = engine.compute_metrics(self.REAL_2027A_DEAL)
        assert 0 <= m["dscr"] <= 20
        assert m["dscr"] == round(1_278_200 / 745_494, 3)

    def test_2027a_equity_pct_is_sane(self):
        m = engine.compute_metrics(self.REAL_2027A_DEAL)
        assert 0 <= m["equity_pct"] <= 100
        assert m["equity_pct"] == round(4_500_000 / 14_500_000 * 100, 2)

    def test_missing_debt_service_raises(self):
        deal = {k: v for k, v in self.STRONG_DEAL.items() if k != "debt_service"}
        try:
            engine.compute_metrics(deal)
            assert False, "expected ValueError for missing debt_service"
        except ValueError:
            pass

    def test_zero_total_project_cost_raises(self):
        deal = dict(self.STRONG_DEAL)
        deal["total_project_cost"] = 0
        try:
            engine.compute_metrics(deal)
            assert False, "expected ValueError for zero total_project_cost"
        except ValueError:
            pass


# ── JPM Benchmark comparison ──────────────────────────────────────

class TestBenchmarks:

    def test_a_grade_thresholds(self):
        a = BENCHMARKS["A"]
        assert a["dscr"] == 2.0
        assert a["ltv"] == 55
        assert a["icr"] == 3.5

    def test_bbb_minus_thresholds(self):
        bbb = BENCHMARKS["BBB_minus"]
        assert bbb["dscr"] == 1.5
        assert bbb["ltv"] == 70
        assert bbb["d_ebitda"] == 6.5

    def test_grade_falls_to_bb_on_single_breach(self):
        """If DSCR is A-grade but LTV breaches, grade degrades."""
        grade = engine._determine_grade(
            dscr=2.5,   # A-grade
            ltv=80,     # breaches everything
            cf_lev=1.0, bs_lev=1.0, d_ebitda=3.0, icr=5.0,
        )
        assert grade == "BB"


# ── score_deal ────────────────────────────────────────────────────

class TestScoreDeal:

    def test_excellent_score(self):
        result = engine.score_deal({
            "dscr": 3.0, "ltv": 40, "cash_flow_leverage": 0.8,
            "balance_sheet_leverage": 1.2, "debt_to_ebitda": 3.0,
            "interest_coverage": 5.0, "sponsor_quality": 10,
            "market_fundamentals": 15,
        })
        assert result["total_score"] >= 85
        assert result["grade"] == "A"
        assert "proceed" in result["recommendation"].lower()

    def test_poor_score(self):
        result = engine.score_deal({
            "dscr": 1.0, "ltv": 85, "cash_flow_leverage": 4.0,
            "balance_sheet_leverage": 5.0, "debt_to_ebitda": 10.0,
            "interest_coverage": 1.0, "sponsor_quality": 2,
            "market_fundamentals": 3,
        })
        assert result["total_score"] < 50
        assert "decline" in result["recommendation"].lower() or "restructure" in result["recommendation"].lower()


# ── compute_lgd ───────────────────────────────────────────────────

class TestLGD:

    def test_bare_lgd(self):
        lgd = engine.compute_lgd({})
        assert lgd == 60.0  # 100 - 40

    def test_bank_conduit_lgd_near_zero(self):
        lgd = engine.compute_lgd({
            "senior_lien": True,
            "bank_manages_proceeds": True,
            "io_funded": True,
            "maturity_reserve_pct": 2.5,
            "lc_coverage_pct": 100,
        })
        assert lgd <= 5.0  # NEST model approaches 0%


# ── capital stack ─────────────────────────────────────────────────

class TestCapitalStack:

    def test_default_split(self):
        stack = engine.compute_capital_stack(100_000_000)
        assert stack["a_amount"] == 75_000_000
        assert stack["b_amount"] == 7_000_000
        assert stack["equity"] == 18_000_000
        assert stack["cltv"] == 82.0


# ── free equity / roll-forward (Ticket 19/17) ──────────────────────

class TestFreeEquity:
    """max(0, AppraisedValue - TotalDebt - Reserves - Holdbacks) — the real,
    re-appraisal-based free equity formula, distinct from
    compute_capital_stack()'s residual sources-and-uses equity figure."""

    def test_standard_case(self):
        fe = engine.free_equity(appraised_value=100_000_000, total_debt=65_000_000)
        assert fe == 35_000_000

    def test_reserves_and_holdbacks_reduce_free_equity(self):
        fe = engine.free_equity(
            appraised_value=100_000_000, total_debt=65_000_000,
            reserves=2_000_000, holdbacks=1_000_000,
        )
        assert fe == 32_000_000

    def test_floors_at_zero_never_negative(self):
        fe = engine.free_equity(appraised_value=50_000_000, total_debt=80_000_000)
        assert fe == 0.0

    def test_generic_across_arbitrary_project_sizes_not_hardcoded(self):
        """Formula must scale as a percentage relationship, not assume any
        specific project's dollar amounts (e.g. Horn Lake's)."""
        small = engine.free_equity(appraised_value=10_000_000, total_debt=6_500_000)
        large = engine.free_equity(appraised_value=1_000_000_000, total_debt=650_000_000)
        assert small == 3_500_000
        assert large == 350_000_000
        assert large == small * 100

    def test_defaults_to_as_completed_basis(self):
        fe = engine.free_equity(appraised_value=100_000_000, total_debt=65_000_000)
        assert fe == 35_000_000  # basis doesn't change the math, only what appraised_value means

    def test_rejects_invalid_valuation_basis(self):
        try:
            engine.free_equity(appraised_value=100_000_000, total_debt=65_000_000, valuation_basis="market")
            assert False, "expected ValueError for invalid valuation_basis"
        except ValueError:
            pass


class TestRollForwardEquity:
    """Ticket 17: a completed phase's re-appraised value, less debt/
    reserves/holdbacks, is the free equity available to fund the next
    phase's capital requirement at a target LTC."""

    def test_equity_fully_funds_next_phase(self):
        result = engine.roll_forward_equity(
            phase_appraised_value=100_000_000, phase_total_debt=65_000_000,
            target_ltc_pct=70, next_phase_cost=100_000_000,
        )
        # free equity = 35M; next phase needs 30M equity (100M - 70M debt capacity)
        assert result["equity_available"] == 35_000_000
        assert result["next_phase_equity_required"] == 30_000_000
        assert result["equity_rolled_forward"] == 30_000_000
        assert result["remaining_equity_gap"] == 0
        assert result["excess_equity_after_roll"] == 5_000_000
        assert result["fully_funded_by_roll_forward"] is True

    def test_equity_gap_when_next_phase_bigger(self):
        result = engine.roll_forward_equity(
            phase_appraised_value=50_000_000, phase_total_debt=35_000_000,
            target_ltc_pct=70, next_phase_cost=100_000_000,
        )
        # free equity = 15M; next phase needs 30M equity — 15M gap remains
        assert result["equity_available"] == 15_000_000
        assert result["next_phase_equity_required"] == 30_000_000
        assert result["equity_rolled_forward"] == 15_000_000
        assert result["remaining_equity_gap"] == 15_000_000
        assert result["fully_funded_by_roll_forward"] is False

    def test_valuation_basis_defaults_to_as_completed_and_is_reported(self):
        result = engine.roll_forward_equity(
            phase_appraised_value=100_000_000, phase_total_debt=65_000_000,
            target_ltc_pct=70, next_phase_cost=100_000_000,
        )
        assert result["valuation_basis"] == "as_completed"

    def test_as_is_basis_explicitly_selectable(self):
        result = engine.roll_forward_equity(
            phase_appraised_value=90_000_000, phase_total_debt=65_000_000,
            target_ltc_pct=70, next_phase_cost=100_000_000,
            valuation_basis="as_is",
        )
        assert result["valuation_basis"] == "as_is"
        assert result["equity_available"] == 25_000_000
