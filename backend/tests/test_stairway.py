"""Tests for Stairway -- the pathway from not-financeable to financeable."""
from services.stairway import build_pathway, propose_alternatives, stairway_full

CLEAN = {
    "sector": "water_sewer", "borrower_type": "governmental",
    "stabilized_dscr": 1.55, "revenue_mechanism": "operating",
    "revenue_mechanism_seasoned": True, "revenue_contracted_pct": 85,
    "operating_history_years": 12, "series_par": 60_000_000,
    "total_debt": 60_000_000, "total_project_cost": 100_000_000,
}

TROUBLED = {
    "sector": "mixed_use", "borrower_type": "developer", "stabilized_dscr": 1.28,
    "tax_exempt_par": 275_000_000, "conduit_issuer_identified": False,
    "public_purpose_established": False, "revenue_mechanism": "special_tax",
    "revenue_mechanism_seasoned": False, "revenue_contracted_pct": 0,
    "operating_history_years": 0, "capitalized_interest_months": 24,
    "revenue_ramp_months": 36, "annual_debt_service": 9_200_000,
    "total_debt": 913_250_000, "total_project_cost": 1_405_000_000,
    "primary_demand_driver": "Ole Miss", "primary_demand_driver_share": 70,
    "series_par": 55_000_000, "phase_funded_by_prior_phase_equity": True,
    "phase_count": 6,
}


class TestPathwayAlwaysExists:
    def test_clean_deal_needs_no_remediation(self):
        p = build_pathway(CLEAN)
        assert p["verdict"] == "NO_REMEDIATION_REQUIRED"
        assert p["steps"] == []

    def test_troubled_deal_still_has_a_pathway(self):
        p = build_pathway(TROUBLED)
        assert p["pathway_exists"] is True
        assert p["step_count"] > 0

    def test_fatal_coverage_still_yields_steps(self):
        """Even a NO_GO deal gets a path -- it just changes the deal."""
        p = build_pathway({**TROUBLED, "stabilized_dscr": 0.9})
        assert p["step_count"] > 0
        assert p["steps_that_change_the_deal"]


class TestEveryStepIsAccountable:
    def test_each_step_names_owner_cost_duration_and_reason(self):
        for s in build_pathway(TROUBLED)["steps"]:
            assert s["control"] in ("SPONSOR", "NEST", "VENDOR",
                                    "COUNTERPARTY", "GOVERNMENTAL", "MARKET")
            assert len(s["cost_usd_range"]) == 2
            assert len(s["duration_weeks_range"]) == 2
            assert s["why"] and s["unlocks"]
            assert s["cost_provenance"] == "HAND_SET_PLANNING_ESTIMATE"

    def test_steps_are_sequenced(self):
        steps = build_pathway(TROUBLED)["steps"]
        assert [s["sequence"] for s in steps] == list(range(1, len(steps) + 1))

    def test_costs_are_labeled_as_estimates_not_quotes(self):
        p = build_pathway(TROUBLED)
        assert "not quotes" in p["disclaimer"]


class TestAlternativesAreNotDoubleCounted:
    """Regression: an OR-branch step was compounded as if it were required,
    making a bridgeable seasoning constraint read as unavoidable."""

    def test_superseded_steps_are_excluded_from_required_count(self):
        p = build_pathway(TROUBLED)
        assert p["required_step_count"] < p["step_count"]
        assert p["steps_avoidable_via_alternative"]

    def test_seasoning_steps_are_superseded_by_the_bridge(self):
        p = build_pathway(TROUBLED)
        avoidable = {a["id"] for a in p["steps_avoidable_via_alternative"]}
        assert {"SEA-1", "SEA-2"} <= avoidable

    def test_avoidable_governmental_steps_drop_out_of_uncontrollable(self):
        p = build_pathway(TROUBLED)
        uncontrollable = {s["id"] for s in p["steps_outside_client_control"]}
        assert "SEA-2" not in uncontrollable


class TestControlHonesty:
    def test_control_breakdown_is_reported(self):
        assert build_pathway(TROUBLED)["control_breakdown"]

    def test_missing_issuer_is_never_a_true_dead_end(self):
        """A missing conduit issuer looks fatal but is not: restructuring
        fully taxable always exists. So the inducement-resolution step
        (governmental, uncontrollable) is correctly superseded and drops out
        of the uncontrollable list. What it costs is a wider coupon and a
        changed deal -- not the financing."""
        p = build_pathway({**CLEAN, "tax_exempt_par": 50_000_000,
                           "conduit_issuer_identified": False})
        step_ids = {s["id"] for s in p["steps"]}
        assert {"ISS-1", "ISS-2", "ISS-3"} <= step_ids

        avoidable = {a["id"] for a in p["steps_avoidable_via_alternative"]}
        assert "ISS-2" in avoidable
        assert "ISS-2" not in {s["id"] for s in p["steps_outside_client_control"]}

        taxable_fallback = next(s for s in p["steps"] if s["id"] == "ISS-3")
        assert taxable_fallback["changes_the_deal"] is True

    def test_feasibility_is_a_ratio(self):
        assert 0.0 <= build_pathway(TROUBLED)["feasibility_score"] <= 1.0


class TestBrief:
    def test_brief_gives_next_three_actions(self):
        b = build_pathway(TROUBLED)["brief"]
        assert len(b["next_three_actions"]) == 3
        assert b["narrative"]

    def test_brief_says_it_is_not_dead(self):
        assert any("not dead" in line
                   for line in build_pathway(TROUBLED)["brief"]["narrative"])


class TestAlternativeStructures:
    def test_troubled_deal_gets_alternatives(self):
        alts = propose_alternatives(TROUBLED)
        ids = {a["id"] for a in alts}
        assert {"ALT-BIFURCATE", "ALT-BRIDGE", "ALT-REPHASE"} <= ids

    def test_scaled_alternative_quantifies_from_client_numbers(self):
        alt = next(a for a in propose_alternatives(TROUBLED)
                   if a["id"] == "ALT-SCALE")
        q = alt["quantified"]
        assert q["debt_supportable"] < q["debt_today"]
        assert q["reduction"] > 0

    def test_every_alternative_states_its_trade_off(self):
        for a in propose_alternatives(TROUBLED):
            assert a["trade_off"] and a["reaches_market"] and a["why"]
            assert "No market comparable" in a["basis"]

    def test_clean_deal_needs_no_alternatives(self):
        assert propose_alternatives(CLEAN) == []


class TestFullRun:
    def test_full_returns_all_three_layers(self):
        r = stairway_full(TROUBLED)
        assert r["preflight"]["verdict"]
        assert r["pathway"]["step_count"] > 0
        assert r["alternative_structures"]
        assert "time-to-market" in r["recommendation"]


class TestRoutes:
    def test_stairway_route(self, client):
        r = client.post("/api/gate-fees/stairway", json={"deal": TROUBLED})
        assert r.status_code == 200
        assert r.get_json()["data"]["pathway_exists"] is True

    def test_stairway_full_route(self, client):
        r = client.post("/api/gate-fees/stairway/full", json={"deal": TROUBLED})
        assert r.status_code == 200
        assert r.get_json()["data"]["alternative_structures"]

    def test_stairway_requires_deal(self, client):
        assert client.post("/api/gate-fees/stairway", json={}).status_code == 400
