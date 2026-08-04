"""
Tests for the platform readiness engine.

This engine's output drives decisions to delete code, so the tests care most
about the two ways it could lie: scoring a live module as absent, or scoring
an absent module as live.

The endpoint-counting test exists because an earlier version counted only
@bp.route() and missed @bp.get/@bp.post, which scored 29 live modules as
zero-endpoint and marked auth and preflight for deletion.
"""
import pytest

from services.platform_readiness import (
    CEILING, MIN_ENDPOINTS_TO_WIRE, VERDICTS, WEIGHTS, PlatformReadinessError,
    by_verdict, reachable_from_routes, scan, score_module,
)


@pytest.fixture(scope="module")
def report():
    return scan()


def _find(report, layer, name):
    return next(m for m in report["modules"]
                if m["layer"] == layer and m["name"] == name)


class TestScan:

    def test_finds_every_layer(self, report):
        assert {m["layer"] for m in report["modules"]} == {
            "routes", "services", "engines", "agents"}

    def test_module_count_is_substantial(self, report):
        """A collapsed scan would silently report everything as fine."""
        assert report["totals"]["modules"] > 100

    def test_every_module_gets_a_known_verdict(self, report):
        assert all(m["verdict"] in VERDICTS for m in report["modules"])

    def test_probability_is_bounded(self, report):
        assert all(0.0 <= m["probability"] <= CEILING
                   for m in report["modules"])


class TestEndpointCounting:
    """The regression that marked auth and preflight for deletion."""

    def test_route_decorator_style_is_counted(self, report):
        # deals.py uses @deals_bp.route(...)
        assert _find(report, "routes", "deals")["endpoints"] > 0

    def test_method_decorator_style_is_counted(self, report):
        # auth.py uses @auth_bp.get / @auth_bp.post exclusively
        assert _find(report, "routes", "auth")["endpoints"] > 0

    def test_no_registered_route_is_silently_zero(self, report):
        """
        A registered blueprint with zero detected endpoints is either genuinely
        empty or a parser miss. Keep the count low enough that a parser
        regression shows up here rather than in a deletion decision.
        """
        empty = [m for m in report["modules"]
                 if m["layer"] == "routes" and m["registered"]
                 and m["endpoints"] == 0]
        assert len(empty) < 10, [m["name"] for m in empty]


class TestReachability:

    def test_registered_routes_are_reachable(self, report):
        for m in report["modules"]:
            if m["layer"] == "routes" and m["registered"]:
                assert m["reachable"], m["name"]

    def test_a_service_a_route_imports_is_reachable(self, report):
        # routes/gate_fees.py imports services/document_package.py
        assert _find(report, "services", "document_package")["reachable"]
        assert _find(report, "services", "gate_fee_engine")["reachable"]

    def test_transitive_import_is_reachable(self, report):
        """
        document_package imports pom_engine, and no route imports pom_engine
        directly. Reachability must follow the chain, not just one hop.
        """
        assert _find(report, "services", "pom_engine")["reachable"]

    def test_unreachable_modules_are_reported_not_hidden(self, report):
        assert report["totals"]["unreachable"] >= 0
        assert (report["totals"]["reachable"]
                + report["totals"]["unreachable"]
                == report["totals"]["modules"])

    def test_graph_walk_terminates_on_a_cycle(self):
        """Circular imports are real; the walk must not hang or recurse away."""
        mods = {
            "routes/a": {"layer": "routes", "registered": True,
                         "imports": {"services/b"}},
            "services/b": {"layer": "services", "registered": False,
                           "imports": {"services/c"}},
            "services/c": {"layer": "services", "registered": False,
                           "imports": {"services/b"}},
            "services/orphan": {"layer": "services", "registered": False,
                                "imports": set()},
        }
        reach = reachable_from_routes(mods)
        assert reach == {"routes/a", "services/b", "services/c"}
        assert "services/orphan" not in reach

    def test_unregistered_route_is_not_an_entry_point(self):
        mods = {
            "routes/dead": {"layer": "routes", "registered": False,
                            "imports": {"services/only_here"}},
            "services/only_here": {"layer": "services", "registered": False,
                                   "imports": set()},
        }
        assert reachable_from_routes(mods) == set()


class TestVerdicts:

    def _mod(self, **kw):
        # has_substance defaults True here so these tests isolate the
        # reachability/wiring/endpoint logic. Hollowness is TestHollowDetection.
        base = {"layer": "routes", "name": "x", "prefix": "/api/x",
                "registered": True, "endpoints": 5, "reachable": True,
                "wired_by": [], "components": [], "tested": False,
                "has_substance": True}
        base.update(kw)
        return base

    def test_unreachable_beats_every_other_signal(self):
        """An unreachable module is absent however good it otherwise looks."""
        m = score_module(self._mod(reachable=False, endpoints=40,
                                   components=["X.tsx"], tested=True))
        assert m["verdict"] == "UNREACHABLE"

    def test_wired_route_reads_wired(self):
        assert score_module(self._mod(wired_by=["A.tsx"]))["verdict"] == "WIRED"

    def test_both_halves_present_means_wire(self):
        m = score_module(self._mod(components=["X.tsx"],
                                   endpoints=MIN_ENDPOINTS_TO_WIRE))
        assert m["verdict"] == "WIRE"

    def test_backend_without_surface_means_build_frontend(self):
        assert score_module(self._mod())["verdict"] == "BUILD_FRONTEND"

    def test_thin_route_means_rebuild(self):
        m = score_module(self._mod(endpoints=MIN_ENDPOINTS_TO_WIRE - 1))
        assert m["verdict"] == "REBUILD"

    def test_registered_route_with_no_endpoints_means_rebuild(self):
        assert score_module(self._mod(endpoints=0))["verdict"] == "REBUILD"

    def test_reachable_service_behind_a_dead_route_is_unused_not_wired(self):
        m = score_module(self._mod(layer="services", prefix=None, endpoints=0))
        assert m["verdict"] == "REACHABLE_UNUSED"

    def test_wiring_raises_the_score(self):
        cold = score_module(self._mod())["probability"]
        warm = score_module(self._mod(wired_by=["A.tsx"]))["probability"]
        assert warm > cold

    def test_one_missing_factor_does_not_collapse_to_zero(self):
        """
        The correction success_predictor needed: a single unmet factor should
        place a module badly, not score it impossible.
        """
        m = score_module(self._mod(tested=False, components=[],
                                   wired_by=["A.tsx"]))
        assert m["probability"] > 0.0


class TestHollowDetection:
    """
    A route can be connected end to end and compute nothing -- a screen
    calling an endpoint that returns a literal defined in its own file. That
    is the most flattering failure mode available, because every dashboard
    reads green. HOLLOW exists to make it visible.
    """

    def _mod(self, **kw):
        base = {"layer": "routes", "name": "x", "prefix": "/api/x",
                "registered": True, "endpoints": 12, "reachable": True,
                "wired_by": ["Screen.tsx"], "components": [], "tested": False,
                "has_substance": True}
        base.update(kw)
        return base

    def test_wired_route_with_no_logic_import_is_hollow(self):
        assert score_module(
            self._mod(has_substance=False))["verdict"] == "HOLLOW"

    def test_wired_route_that_calls_logic_is_wired(self):
        assert score_module(self._mod())["verdict"] == "WIRED"

    def test_hollow_scores_below_wired(self):
        """Endpoint count must not compensate for computing nothing."""
        hollow = score_module(self._mod(has_substance=False, endpoints=40))
        wired = score_module(self._mod(endpoints=3))
        assert hollow["probability"] < wired["probability"]

    def test_hollow_names_the_fix_as_a_body_not_a_connection(self):
        why = score_module(self._mod(has_substance=False))["why"]
        assert "body" in why and "connection" in why

    def test_non_route_layers_are_not_judged_on_substance(self, report):
        """A service IS the logic; asking whether it imports logic is wrong."""
        for m in report["modules"]:
            if m["layer"] != "routes":
                assert m["has_substance"] is True

    def test_known_hollow_routes_are_caught(self, report):
        """
        phoenix and treasury each expose double-digit endpoints, import
        nothing, and sit beside a substantial unused engine. If a change makes
        these read WIRED, the detector has stopped working.
        """
        for name in ("phoenix", "treasury"):
            m = _find(report, "routes", name)
            if m["wired_by"]:
                assert m["verdict"] == "HOLLOW", name
                assert m["imports_logic"] is False, name


class TestReporting:

    def test_weights_declare_their_provenance(self, report):
        assert report["provenance"]["weights_provenance"] == "HAND_SET"
        assert set(report["provenance"]["weights"]) == set(WEIGHTS)

    def test_approximate_inputs_are_labelled(self, report):
        """Name-overlap matching must never be presented as exact."""
        assert any("name overlap" in s
                   for s in report["provenance"]["approximate"])

    def test_scope_note_refuses_to_claim_correctness(self, report):
        assert "does not mean correct" in report["scope_note"]

    def test_verdict_counts_reconcile(self, report):
        assert sum(report["by_verdict"].values()) == report["totals"]["modules"]

    def test_by_verdict_filters(self):
        for m in by_verdict("UNREACHABLE"):
            assert m["verdict"] == "UNREACHABLE"

    def test_unknown_verdict_rejected(self):
        with pytest.raises(PlatformReadinessError):
            by_verdict("PROBABLY_FINE")
