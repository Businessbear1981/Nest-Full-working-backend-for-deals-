"""Tests for structural viability preflight."""
from services.preflight import run_preflight

CLEAN = {
    "sector": "water_sewer", "borrower_type": "governmental",
    "stabilized_dscr": 1.55, "revenue_mechanism": "operating",
    "revenue_mechanism_seasoned": True, "revenue_contracted_pct": 85,
    "operating_history_years": 12, "series_par": 60_000_000,
    "total_debt": 60_000_000, "total_project_cost": 100_000_000,
}


class TestVerdicts:
    def test_clean_deal_proceeds(self):
        assert run_preflight(CLEAN)["verdict"] == "PROCEED"

    def test_fatal_coverage_is_no_go_and_signals_walk(self):
        r = run_preflight({**CLEAN, "stabilized_dscr": 0.95})
        assert r["verdict"] == "NO_GO"
        assert r["walk_away_signal"] is True
        assert r["no_go"][0]["code"] == "COVERAGE_FATAL"

    def test_tax_exempt_with_no_issuer_is_no_go(self):
        r = run_preflight({**CLEAN, "tax_exempt_par": 100_000_000,
                           "conduit_issuer_identified": False})
        assert r["walk_away_signal"] is True
        assert any(t["code"] == "NO_CONDUIT_ISSUER" for t in r["no_go"])

    def test_structural_trap_yields_restructure_not_walk(self):
        r = run_preflight({**CLEAN, "stabilized_dscr": 1.15})
        assert r["verdict"] == "RESTRUCTURE"
        assert r["walk_away_signal"] is False


class TestTraps:
    def test_private_use_tax_exemption_flagged(self):
        r = run_preflight({**CLEAN, "sector": "hotel", "borrower_type": "developer",
                           "tax_exempt_par": 275_000_000,
                           "conduit_issuer_identified": True,
                           "public_purpose_established": False})
        assert any(t["code"] == "TAX_EXEMPT_INELIGIBLE" for t in r["structural"])

    def test_capi_shorter_than_ramp_flagged(self):
        r = run_preflight({**CLEAN, "capitalized_interest_months": 18,
                           "revenue_ramp_months": 36})
        t = next(t for t in r["structural"] if t["code"] == "CAPI_EXHAUSTION")
        assert "18 month gap" in t["evidence"]

    def test_capi_covering_ramp_is_clear(self):
        r = run_preflight({**CLEAN, "capitalized_interest_months": 40,
                           "revenue_ramp_months": 36})
        assert not any(t["code"] == "CAPI_EXHAUSTION" for t in r["structural"])

    def test_unseasoned_assessment_flagged(self):
        r = run_preflight({**CLEAN, "revenue_mechanism": "special_assessment",
                           "revenue_mechanism_seasoned": False})
        assert any(t["code"] == "UNSEASONED_ASSESSMENT" for t in r["structural"])

    def test_overleverage_flagged(self):
        r = run_preflight({**CLEAN, "total_debt": 95_000_000,
                           "total_project_cost": 100_000_000})
        assert any(t["code"] == "OVERLEVERED" for t in r["structural"])

    def test_bank_qualified_small_series_is_not_flagged(self):
        """A $10M tax-exempt series is a real BQ execution, not a defect."""
        r = run_preflight({**CLEAN, "series_par": 10_000_000, "tax_exempt": True})
        assert not any(t["code"] == "SERIES_TOO_SMALL" for t in r["watch"])

    def test_phasing_cascade_flagged_as_watch(self):
        r = run_preflight({**CLEAN, "phase_funded_by_prior_phase_equity": True,
                           "phase_count": 6})
        assert any(t["code"] == "PHASING_CASCADE" for t in r["watch"])


class TestHonesty:
    def test_missing_inputs_reported_not_guessed(self):
        r = run_preflight({})
        assert r["cannot_assess"]
        assert r["assessment_completeness"] < 1.0
        codes = {c.get("code") for c in r["cannot_assess"]}
        assert "COVERAGE" in codes

    def test_every_trap_cites_evidence_and_a_fix(self):
        r = run_preflight({**CLEAN, "stabilized_dscr": 1.15,
                           "revenue_mechanism": "special_tax",
                           "revenue_mechanism_seasoned": False})
        for band in ("no_go", "structural", "watch"):
            for t in r[band]:
                assert t["evidence"] and t["fix"] and t["why"]


class TestRoute:
    def test_preflight_route(self, client):
        r = client.post("/api/gate-fees/preflight", json={"deal": CLEAN})
        assert r.status_code == 200
        assert r.get_json()["data"]["verdict"] == "PROCEED"

    def test_preflight_requires_deal(self, client):
        assert client.post("/api/gate-fees/preflight", json={}).status_code == 400
