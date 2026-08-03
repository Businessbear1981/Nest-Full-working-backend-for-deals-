"""HTTP tests for the Rico routes -- /api/eagleeye/comparable-deals and
/api/eagleeye/pooled-offering.

The engines behind these were already covered by test_pooled_offering.py;
what is tested here is that they are actually reachable over HTTP and that
the route layer does not fabricate a pool when the inputs are thin.
"""

DEALS = [
    {"id": "d1", "name": "CCRC A", "sector": "senior_living", "bond_face": 60_000_000,
     "dscr": 1.5, "ltv": 65, "rating": "Baa1", "noi": 6_000_000},
    {"id": "d2", "name": "CCRC B", "sector": "senior_living", "bond_face": 40_000_000,
     "dscr": 1.4, "ltv": 68, "rating": "Baa2", "noi": 3_500_000},
    {"id": "d3", "name": "CCRC C", "sector": "senior_living", "bond_face": 50_000_000,
     "dscr": 1.55, "ltv": 63, "rating": "A3", "noi": 5_200_000},
]

TARGET = {"id": "t1", "name": "CCRC Target", "sector": "senior_living",
          "bond_face": 55_000_000, "dscr": 1.48, "ltv": 66, "rating": "Baa1",
          "noi": 5_400_000}


class TestComparableDealsRoute:
    def test_route_exists_and_scores_supplied_candidates(self, client):
        resp = client.post("/api/eagleeye/comparable-deals", json={
            "target_deal": TARGET,
            "candidate_deals": DEALS,
            "min_score": 0.0,
        })
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["target_deal_id"] == "t1"
        assert data["candidate_source"] == "supplied"
        assert data["candidates_scanned"] == 3
        assert len(data["matches"]) > 0

    def test_missing_target_deal_is_400(self, client):
        resp = client.post("/api/eagleeye/comparable-deals", json={})
        assert resp.status_code == 400

    def test_bad_candidate_type_is_400(self, client):
        resp = client.post("/api/eagleeye/comparable-deals", json={
            "target_deal": TARGET, "candidate_deals": "not-a-list",
        })
        assert resp.status_code == 400


class TestPooledOfferingRoute:
    def test_explicit_pool_structures(self, client):
        resp = client.post("/api/eagleeye/pooled-offering", json={"deals": DEALS})
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["viable"] is True
        assert data["total_par_usd"] == 150_000_000

    def test_pool_under_floor_is_not_viable_but_still_200(self, client):
        resp = client.post("/api/eagleeye/pooled-offering", json={"deals": DEALS[:2]})
        assert resp.status_code == 200
        assert resp.get_json()["data"]["viable"] is False

    def test_match_then_structure_includes_target_in_its_own_pool(self, client):
        resp = client.post("/api/eagleeye/pooled-offering", json={
            "target_deal": TARGET,
            "candidate_deals": DEALS,
            "min_score": 0.0,
        })
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "matching" in data
        pool_ids = {d["deal_id"] for d in data["deals"]}
        assert "t1" in pool_ids
        # Target par is counted in the offering, not treated as an outside ref.
        assert data["total_par_usd"] == 205_000_000

    def test_neither_deals_nor_target_is_400(self, client):
        resp = client.post("/api/eagleeye/pooled-offering", json={})
        assert resp.status_code == 400

    def test_no_fabricated_pool_when_no_candidates_match(self, client):
        """A target with no comparable universe must come back not-viable --
        never a pool padded out with invented deals."""
        resp = client.post("/api/eagleeye/pooled-offering", json={
            "target_deal": TARGET,
            "candidate_deals": [],
        })
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["viable"] is False
        assert data["pool_size"] == 1
