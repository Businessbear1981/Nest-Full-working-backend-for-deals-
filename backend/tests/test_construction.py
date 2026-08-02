"""Regression tests for routes/construction.py -- fixes the bug where any
real deal_id silently got back the "Convivial St. Petersburg" fixture
instead of that deal's own data (or an honest 404). See docs/NEST_GLOSSARY.md
Executive Summary point 6."""


class TestKnownFixtureStillWorks:
    def test_convivial_returns_its_own_fixture(self, client):
        resp = client.get("/api/construction/deals/convivial-st-pete/summary")
        body = resp.get_json()
        assert resp.status_code == 200
        assert body["data"]["id"] == "convivial-st-pete"
        assert body["data"]["name"] == "Convivial St. Petersburg"
        assert len(body["data"]["milestones"]) == 10


class TestUnknownDealIdNoLongerReturnsFixture:
    def test_random_deal_id_does_not_get_convivial_data(self, client):
        resp = client.get("/api/construction/deals/some-other-real-deal-999/summary")
        body = resp.get_json()
        # Must NOT silently be the Convivial fixture under a different id
        assert body["data"] is None or body["data"].get("name") != "Convivial St. Petersburg"

    def test_unknown_deal_id_with_no_live_match_is_a_real_404(self, client):
        resp = client.get("/api/construction/deals/definitely-does-not-exist-anywhere/summary")
        assert resp.status_code == 404
        body = resp.get_json()
        assert body["success"] is False
        assert "definitely-does-not-exist-anywhere" in body["error"]

    def test_patch_milestone_on_unknown_deal_is_404_not_silent_mutation(self, client):
        resp = client.patch(
            "/api/construction/deals/nonexistent-deal/milestones/m1",
            json={"completion_pct": 50},
        )
        assert resp.status_code == 404

    def test_patch_draw_on_unknown_deal_is_404_not_silent_mutation(self, client):
        resp = client.patch(
            "/api/construction/deals/nonexistent-deal/draws/d1",
            json={"status": "funded"},
        )
        assert resp.status_code == 404


class TestFixtureMutationsStillScopedToFixture:
    def test_patch_milestone_on_convivial_still_works(self, client):
        resp = client.patch(
            "/api/construction/deals/convivial-st-pete/milestones/m6",
            json={"completion_pct": 25},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["completion_pct"] == 25
