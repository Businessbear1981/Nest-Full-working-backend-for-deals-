"""
Tests for the POM engine.

The engine exists to replace one hand-set number (196 hours) with a derived
one. So the tests care about two things: that the derivation actually responds
to the engagement structure, and that it refuses to claim a section can be
written when its input does not exist.
"""
import pytest

from services.pom_engine import (
    COUNSEL_RESERVED, DRAFTING_MODELS, LEGACY_HAND_SET_POM_HOURS, POMError,
    compare_drafting_models, plan_pom,
)

# A deal with every input satisfied, so blocking never confounds an hours test.
COMPLETE = {k: True for k in [
    "par_amount", "maturity_schedule", "capital_stack", "project_budget",
    "trust_indenture", "revenue_mechanism", "project_description",
    "site_control", "org_structure", "feasibility_study", "audited_financials",
    "financial_projections", "bond_counsel_engaged", "tax_status_determination",
    "rating", "underwriter_engaged",
]}


class TestDraftingModels:

    def test_hours_rise_with_nest_holding_more_of_the_pen(self):
        h = {m: plan_pom(COMPLETE, drafting_model=m)["hours"]["total"]
             for m in DRAFTING_MODELS}
        assert h["counsel_drafts"] < h["market_standard"] < h["nest_drafts_all"]

    def test_counsel_drafts_means_nest_drafts_nothing(self):
        p = plan_pom(COMPLETE, drafting_model="counsel_drafts")
        assert p["hours"]["drafting"] == 0
        assert all(s["nest_role"] == "REVIEW" for s in p["sections"])

    def test_counsel_reserved_sections_are_never_drafted_by_nest(self):
        """NEST does not draft a tax opinion under any engagement structure."""
        for model in DRAFTING_MODELS:
            p = plan_pom(COMPLETE, drafting_model=model)
            for s in p["sections"]:
                if s["id"] in COUNSEL_RESERVED:
                    assert s["nest_role"] == "REVIEW", (model, s["id"])

    def test_unknown_model_is_rejected(self):
        with pytest.raises(POMError):
            plan_pom(COMPLETE, drafting_model="whoever_is_free")

    def test_negative_comment_cycles_rejected(self):
        with pytest.raises(POMError):
            plan_pom(COMPLETE, comment_cycles=-1)

    def test_comment_cycles_move_the_total(self):
        few = plan_pom(COMPLETE, comment_cycles=2)["hours"]["total"]
        many = plan_pom(COMPLETE, comment_cycles=8)["hours"]["total"]
        assert many > few

    def test_legacy_figure_falls_between_two_models(self):
        """
        The point of the engine: 196 was not a wrong answer to a stated
        question, it was an answer to an unstated one. It sits between the
        cheapest and the standard model, matching neither.
        """
        h = {m: plan_pom(COMPLETE, drafting_model=m)["hours"]["total"]
             for m in DRAFTING_MODELS}
        assert h["counsel_drafts"] < LEGACY_HAND_SET_POM_HOURS < h["nest_drafts_all"]

    def test_variance_is_reported_against_legacy(self):
        p = plan_pom(COMPLETE)
        v = p["variance_from_legacy"]
        assert v["delta"] == v["derived_hours"] - LEGACY_HAND_SET_POM_HOURS


class TestConditionalSections:

    def test_rating_section_absent_when_not_rated(self):
        ids = [s["id"] for s in plan_pom({})["sections"]]
        assert "rating" not in ids

    def test_rating_section_present_when_seeking_a_rating(self):
        ids = [s["id"] for s in plan_pom({"seeking_rating": True})["sections"]]
        assert "rating" in ids

    def test_private_placement_drops_the_underwriting_section(self):
        ids = [s["id"] for s in
               plan_pom({"distribution_method": "private_placement"})["sections"]]
        assert "underwriting" not in ids

    def test_enhancement_section_appears_only_when_enhanced(self):
        assert "credit_enhancement" not in [
            s["id"] for s in plan_pom({})["sections"]]
        assert "credit_enhancement" in [
            s["id"] for s in plan_pom({"credit_enhancement": True})["sections"]]


class TestBlocking:

    def test_empty_deal_blocks_nearly_everything(self):
        r = plan_pom({})["readiness"]
        assert r["sections_blocked"] > 0
        assert r["pct_writable"] < 0.5

    def test_complete_deal_blocks_nothing(self):
        r = plan_pom(COMPLETE)["readiness"]
        assert r["sections_blocked"] == 0
        assert r["pct_writable"] == 1.0
        assert r["critical_inputs"] == []

    def test_critical_inputs_ranked_by_sections_blocked(self):
        r = plan_pom({})["readiness"]
        counts = [c["blocks_sections"] for c in r["critical_inputs"]]
        assert counts == sorted(counts, reverse=True)

    def test_blocked_section_names_the_input_it_is_waiting_on(self):
        p = plan_pom({**COMPLETE, "feasibility_study": False})
        blocked = {s["id"]: s["missing_inputs"] for s in p["sections"]
                   if s["blocked"]}
        assert "feasibility_summary" in blocked
        assert blocked["feasibility_summary"] == ["feasibility_study"]

    def test_blocking_does_not_change_the_hours(self):
        """Hours are what the work costs; blocking is when it can start."""
        a = plan_pom(COMPLETE)["hours"]["total"]
        b = plan_pom({**COMPLETE, "feasibility_study": False})["hours"]["total"]
        assert a == b


class TestComparison:

    def test_comparison_covers_every_model(self):
        c = compare_drafting_models(COMPLETE)
        assert set(c["models"]) == set(DRAFTING_MODELS)
        assert c["spread_hours"] > 0

    def test_comparison_declines_to_recommend(self):
        """
        Choosing a drafting model trades legal cost against control of how the
        credit is characterised. That is not an engine's call to make.
        """
        c = compare_drafting_models(COMPLETE)
        assert "recommended" not in c
        assert "recommendation" not in c


class TestRoutes:

    def test_plan_over_http(self, client):
        r = client.post("/api/gate-fees/pom/plan",
                        json={"deal": COMPLETE, "drafting_model": "counsel_drafts"})
        assert r.status_code == 200
        d = r.get_json()["data"]
        assert d["drafting_model"] == "counsel_drafts"
        assert d["hours"]["drafting"] == 0

    def test_plan_defaults_to_market_standard(self, client):
        r = client.post("/api/gate-fees/pom/plan", json={})
        assert r.status_code == 200
        assert r.get_json()["data"]["drafting_model"] == "market_standard"

    def test_bad_model_is_400_not_500(self, client):
        r = client.post("/api/gate-fees/pom/plan",
                        json={"drafting_model": "nope"})
        assert r.status_code == 400

    def test_compare_over_http(self, client):
        r = client.post("/api/gate-fees/pom/compare", json={"deal": COMPLETE})
        assert r.status_code == 200
        assert set(r.get_json()["data"]["models"]) == set(DRAFTING_MODELS)

    def test_sections_catalogue_is_readable(self, client):
        r = client.get("/api/gate-fees/pom/sections")
        assert r.status_code == 200
        d = r.get_json()["data"]
        # The full catalogue, including conditional sections. A given deal
        # sees fewer -- an unrated private placement drops three.
        assert len(d["sections"]) == 23
        assert "tax_matters" in d["counsel_reserved"]
