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


class TestProvenance:
    """Regression: a hand-set threshold must never read as market evidence."""

    def test_every_trap_declares_its_provenance(self):
        r = run_preflight({**CLEAN, "stabilized_dscr": 1.15,
                           "revenue_mechanism": "special_tax",
                           "revenue_mechanism_seasoned": False})
        for band in ("no_go", "structural", "watch"):
            for t in r[band]:
                assert t["threshold_provenance"] in (
                    "HAND_SET", "RULE_BASED", "MARKET_DERIVED")

    def test_calibration_status_reports_zero_not_aspiration(self):
        from services.preflight import calibration_status
        c = calibration_status()
        assert c["calibration_coverage"] == 0.0
        assert c["market_derived_thresholds"] == []
        assert c["minimum_sample_for_calibration"] >= 30
        assert "hand-set assumptions" in c["honest_status"]

    def test_preflight_result_carries_calibration(self):
        assert "calibration" in run_preflight(CLEAN)

    def test_emma_calibratable_traps_are_named(self):
        from services.preflight import EMMA_CALIBRATABLE
        assert "UNSEASONED_ASSESSMENT" in EMMA_CALIBRATABLE
        assert "CAPI_EXHAUSTION" in EMMA_CALIBRATABLE


class TestEmmaProvenance:
    def test_seed_bonds_are_not_counted_as_verified_filings(self):
        from services.emma_seed_data import seed_emma_database
        from services.emma_engine import seed_modeled, verified_filings
        seed_emma_database()
        assert len(seed_modeled()) >= 10
        assert all(not b.get("is_verified_emma_filing") for b in seed_modeled())
        assert all(b.get("is_verified_emma_filing", True)
                   for b in verified_filings())

    def test_seed_bonds_no_longer_claim_an_emma_url(self):
        """Regression: seed data used to carry a fabricated emma.msrb.org URL."""
        from services.emma_seed_data import SEED_BONDS, seed_emma_database
        seed_emma_database()
        for b in SEED_BONDS:
            assert not (b.get("source_url") or "").startswith("https://emma.msrb.org")
            assert b["provenance_note"]

    def test_stats_splits_verified_from_modeled(self):
        from services.emma_seed_data import seed_emma_database
        from services.emma_engine import EMMAEngine
        seed_emma_database()
        s = EMMAEngine().stats()
        assert "verified_emma_filings" in s
        assert "seed_modeled_structures" in s
        assert s["seed_modeled_structures"] >= 10
