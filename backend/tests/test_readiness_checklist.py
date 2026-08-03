"""Tests for the Project Readiness Checklist intake module."""
import pytest

from services.readiness_checklist import (
    MOVE_FORWARD_THRESHOLD, checklist_catalogue, derive_deal_parameters,
    intake, rag, score_readiness,
)

CAT = checklist_catalogue()
ALL_ITEMS = [i["num"] for c in CAT["categories"]
             for s in c["subcategories"] for i in s["items"]]


class TestCatalogue:
    def test_full_checklist_loaded(self):
        assert CAT["total_items"] == 272
        assert len(CAT["categories"]) == 8

    def test_threshold_matches_the_dsa(self):
        assert CAT["move_forward_threshold"] == 0.80


class TestScoring:
    def test_everything_available_is_100_and_clears(self):
        r = score_readiness({i: "available" for i in ALL_ITEMS})
        assert r["readiness_score"] == 1.0
        assert r["move_forward_memorandum"]["issues"] is True
        assert r["gap_count"] == 0

    def test_nothing_submitted_is_zero_and_blocks(self):
        r = score_readiness({})
        assert r["readiness_score"] == 0.0
        assert r["move_forward_memorandum"]["issues"] is False
        assert "refundable" in r["move_forward_memorandum"]["consequence"]
        assert r["gap_count"] == 272

    def test_na_with_justification_is_excluded_from_both_sides(self):
        subs = {i: "available" for i in ALL_ITEMS}
        subs[ALL_ITEMS[0]] = {"status": "not_applicable", "justification": "No parent co."}
        r = score_readiness(subs)
        assert r["items_applicable"] == 271
        assert r["excluded_not_applicable"] == 1
        assert r["readiness_score"] == 1.0

    def test_na_without_justification_counts_against_you(self):
        """Regression: unjustified N/A must not be a free pass to inflate score."""
        subs = {i: "available" for i in ALL_ITEMS}
        subs[ALL_ITEMS[0]] = "not_applicable"
        r = score_readiness(subs)
        assert r["items_applicable"] == 272
        assert r["not_applicable_rejected_no_justification"] == 1
        assert r["readiness_score"] < 1.0

    def test_gap_analysis_names_the_missing_item(self):
        r = score_readiness({})
        g = r["gap_analysis"][0]
        assert g["item"] and g["text"] and g["category"]


class TestRAG:
    def test_bands(self):
        assert rag(0.95) == "green"
        assert rag(0.80) == "green"
        assert rag(0.65) == "amber"
        assert rag(0.20) == "red"
        assert rag(None) == "grey"

    def test_board_reports_every_process(self):
        r = score_readiness({i: "available" for i in ALL_ITEMS})
        assert len(r["board"]) == 8
        assert all(row["rag"] == "green" for row in r["board"])
        assert r["rag_summary"]["green"] == 8


class TestParameterDerivation:
    def test_complete_checklist_evidences_parameters(self):
        r = score_readiness({i: "available" for i in ALL_ITEMS})
        d = derive_deal_parameters(r)
        assert d["financial_model"] is True
        assert d["audited_financials"] is True
        assert d["permits_status"] == 100.0

    def test_empty_checklist_evidences_nothing(self):
        d = derive_deal_parameters(score_readiness({}))
        assert all(v is False or v == 0.0 for v in d.values())


class TestIntake:
    def test_intake_joins_readiness_to_prediction(self):
        r = intake({i: "available" for i in ALL_ITEMS},
                   deal_overrides={"projected_dscr": 1.5, "issuer_identified": True,
                                   "market_window": True, "enhancement_committed": True,
                                   "equity_committed_pct": 100})
        assert r["engagement_can_begin"] is True
        assert r["prediction"]["probability_of_close_as_is"] > 0.5
        assert "Readiness 100.0%" in r["summary"]

    def test_thin_intake_blocks_engagement(self):
        r = intake({})
        assert r["engagement_can_begin"] is False
        assert r["prediction"]["stall_point"]["gate_id"]

    def test_overrides_beat_derived_values(self):
        r = intake({i: "available" for i in ALL_ITEMS},
                   deal_overrides={"audited_financials": False})
        assert r["derived_parameters"]["audited_financials"] is True
        assert r["parameters_used"]["audited_financials"] is False


class TestRoutes:
    def test_catalogue_route(self, client):
        r = client.get("/api/gate-fees/readiness/checklist")
        assert r.status_code == 200
        assert r.get_json()["data"]["total_items"] == 272

    def test_score_route(self, client):
        r = client.post("/api/gate-fees/readiness/score",
                        json={"submissions": {i: "available" for i in ALL_ITEMS}})
        assert r.status_code == 200
        assert r.get_json()["data"]["readiness_score"] == 1.0

    def test_score_route_requires_submissions(self, client):
        assert client.post("/api/gate-fees/readiness/score", json={}).status_code == 400

    def test_intake_route(self, client):
        r = client.post("/api/gate-fees/readiness/intake",
                        json={"submissions": {}, "deal_overrides": {"projected_dscr": 1.4}})
        assert r.status_code == 200
        assert r.get_json()["data"]["engagement_can_begin"] is False
