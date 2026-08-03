"""Tests for the gate fee engine, engagement economics, and their routes.

Core invariant under test: no fee is ever payable before the work is
delivered and accepted, and transaction-based fees never accrue while
unlicensed.
"""
import pytest

from services.gate_fee_engine import GateFeeError, gate_fee_engine
from services.engagement_economics import (
    optimize_engagement, value_equity, value_gated_fees, value_success_fee,
)

PAR = 55_000_000


def _ledger(**kw):
    base = dict(series_name="2027B", par=PAR, development_fee_bp=55,
                placement_fee_bp=100, placement_licensed=False)
    base.update(kw)
    return gate_fee_engine.build_ledger(**base)


class TestNoUpfront:
    def test_nothing_is_due_at_signing(self):
        L = _ledger()
        assert L["upfront_due"] == 0.0
        assert all(g["status"] == "pending" for g in L["gates"])
        assert all(g["paid_at"] is None for g in L["gates"])

    def test_client_view_reports_zero_upfront(self):
        assert gate_fee_engine.client_view(_ledger())["money"]["upfront_paid"] == 0.0

    def test_development_weights_sum_to_full_pool(self):
        L = _ledger()
        dev = [g for g in L["gates"] if g["fee_class"] == "development"]
        assert sum(g["amount"] for g in dev) == pytest.approx(
            L["fee_pools"]["development"], rel=1e-6)


class TestFeesScaleWithPar:
    def test_bigger_series_pays_more_at_same_rate(self):
        small = _ledger(par=10_000_000)["fee_pools"]["development"]
        big = _ledger(par=92_000_000)["fee_pools"]["development"]
        assert big > small

    def test_zero_par_rejected(self):
        with pytest.raises(GateFeeError):
            _ledger(par=0)


class TestLicenseGate:
    def test_placement_fees_are_zero_while_unlicensed(self):
        L = _ledger(placement_licensed=False)
        plc = [g for g in L["gates"] if g["fee_class"] == "placement"]
        assert plc and all(g["amount"] == 0 for g in plc)
        assert all(g["blocked_reason"] for g in plc)

    def test_placement_gate_cannot_advance_while_unlicensed(self):
        L = _ledger(placement_licensed=False)
        with pytest.raises(GateFeeError, match="placement_licensed"):
            gate_fee_engine.advance_gate(L, "g10_closing", "accepted")

    def test_placement_fees_exist_once_licensed(self):
        L = _ledger(placement_licensed=True)
        assert L["fee_pools"]["placement"] > 0


class TestPayOnDelivery:
    def test_cannot_pay_a_gate_that_was_never_accepted(self):
        L = _ledger()
        with pytest.raises(GateFeeError, match="accepted first"):
            gate_fee_engine.advance_gate(L, "g1_readiness", "paid")

    def test_accepted_then_paid_is_allowed(self):
        L = _ledger()
        gate_fee_engine.advance_gate(L, "g1_readiness", "accepted")
        gate_fee_engine.advance_gate(L, "g1_readiness", "paid")
        g = next(x for x in L["gates"] if x["id"] == "g1_readiness")
        assert g["paid_at"] is not None
        assert gate_fee_engine.client_view(L)["money"]["paid_to_date"] == g["amount"]

    def test_unknown_gate_rejected(self):
        with pytest.raises(GateFeeError):
            gate_fee_engine.advance_gate(_ledger(), "g99_nope", "accepted")


class TestEconomics:
    def test_paid_gates_are_worth_face_not_discounted(self):
        L = _ledger()
        gate_fee_engine.advance_gate(L, "g1_readiness", "accepted")
        gate_fee_engine.advance_gate(L, "g1_readiness", "paid")
        v = value_gated_fees(L)
        assert v["banked"] > 0
        assert v["pv"] >= v["banked"]

    def test_gated_value_excludes_placement_gates(self):
        """Regression: placement gates were once counted into the gated pool,
        double-counting the success fee into the near-certain bucket."""
        L = _ledger(placement_licensed=True, placement_fee_bp=300)
        assert value_gated_fees(L)["face"] == pytest.approx(
            L["fee_pools"]["development"], rel=1e-6)

    def test_success_fee_uncollectable_while_unlicensed(self):
        v = value_success_fee(par=PAR, fee_bp=225, years_to_close=2,
                              licensed_by_close=False)
        assert v["pv"] == 0.0
        assert v["collectable"] is False
        assert v["face"] > 0  # face still reported honestly

    def test_deferred_success_fee_is_worth_less_than_face(self):
        v = value_success_fee(par=PAR, fee_bp=225, years_to_close=8,
                              licensed_by_close=True)
        assert 0 < v["pv"] < v["face"]


class TestEquityPhantomTax:
    def test_no_tax_provision_produces_warning_and_cost(self):
        v = value_equity(interest_pct=2.0, program_terminal_value=400_000_000,
                         years_to_realization=12,
                         annual_allocated_income=8_000_000,
                         years_of_phantom_income=10,
                         tax_distribution_provision=False)
        assert v["warning"] is not None
        assert v["phantom_tax_pv"] < 0
        assert v["pv"] < v["upside_pv"]

    def test_tax_provision_removes_the_drag(self):
        kw = dict(interest_pct=2.0, program_terminal_value=400_000_000,
                  years_to_realization=12, annual_allocated_income=8_000_000,
                  years_of_phantom_income=10)
        with_prov = value_equity(tax_distribution_provision=True, **kw)
        assert with_prov["phantom_tax_pv"] == 0
        assert with_prov["warning"] is None
        assert with_prov["pv"] > value_equity(
            tax_distribution_provision=False, **kw)["pv"]


class TestOptimizer:
    def test_prefers_gated_fees_over_deferred_success_fees(self):
        o = optimize_engagement(par=PAR, years_to_close=2.0,
                                licensed_by_close=True,
                                client_cost_ceiling_bp=362.5)
        best = o["recommended"]
        assert best["development_fee_bp"] == max(
            c["development_fee_bp"] for c in o["all_candidates"])

    def test_unlicensed_close_yields_no_success_pv(self):
        o = optimize_engagement(par=PAR, years_to_close=2.0,
                                licensed_by_close=False,
                                client_cost_ceiling_bp=362.5)
        assert o["recommended"]["success_pv"] == 0.0

    def test_ceiling_is_respected(self):
        o = optimize_engagement(par=PAR, years_to_close=2.0,
                                licensed_by_close=True,
                                client_cost_ceiling_bp=50)
        for c in o["all_candidates"]:
            assert c["development_fee_bp"] + c["success_fee_bp"] == pytest.approx(50)


class TestRoutes:
    def test_build_advance_and_view_over_http(self, client):
        r = client.post("/api/gate-fees/ledger", json={
            "series_name": "2027A", "par": 10_000_000,
            "development_fee_bp": 90, "placement_fee_bp": 100})
        assert r.status_code == 200
        L = r.get_json()["data"]
        assert L["upfront_due"] == 0.0

        r = client.post("/api/gate-fees/advance", json={
            "ledger": L, "gate_id": "g1_readiness", "status": "accepted"})
        assert r.status_code == 200
        L = r.get_json()["data"]

        r = client.post("/api/gate-fees/client-view", json={"ledger": L})
        assert r.status_code == 200
        assert r.get_json()["data"]["money"]["invoiceable_now"] > 0

    def test_paying_unaccepted_gate_is_400(self, client):
        L = client.post("/api/gate-fees/ledger", json={
            "series_name": "X", "par": 10_000_000,
            "development_fee_bp": 90}).get_json()["data"]
        r = client.post("/api/gate-fees/advance", json={
            "ledger": L, "gate_id": "g2_capital_stack", "status": "paid"})
        assert r.status_code == 400

    def test_program_rollup_over_http(self, client):
        ls = [client.post("/api/gate-fees/ledger", json={
            "series_name": n, "par": p, "development_fee_bp": 60}
        ).get_json()["data"] for n, p in [("2027A", 10e6), ("2027B", 55e6)]]
        r = client.post("/api/gate-fees/program-rollup", json={"ledgers": ls})
        assert r.status_code == 200
        d = r.get_json()["data"]
        assert d["series_count"] == 2
        assert d["upfront_paid"] == 0.0

    def test_gate_catalogue_is_readable(self, client):
        r = client.get("/api/gate-fees/gates")
        assert r.status_code == 200
        assert len(r.get_json()["data"]["development_gates"]) == 8
