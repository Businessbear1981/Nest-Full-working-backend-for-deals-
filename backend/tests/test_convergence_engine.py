"""Tests for ConvergenceEngine — Ticket 18: fabricated demo data must never
be presented as real detection capability."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.convergence_engine import ConvergenceEngine


class TestProductionDefaultHasNoFabricatedData:
    def test_default_construction_seeds_nothing(self):
        engine = ConvergenceEngine()
        assert engine.get_signals() == []
        assert engine.get_heat_events() == []

    def test_default_stats_are_all_zero(self):
        engine = ConvergenceEngine()
        stats = engine.stats()
        assert stats["total_signals"] == 0
        assert stats["real_signals"] == 0
        assert stats["demo_signals"] == 0
        assert stats["heat_events"] == 0


class TestDemoDataIsTagged:
    def test_seed_demo_true_tags_every_signal_as_demo(self):
        engine = ConvergenceEngine(seed_demo=True)
        signals = engine.get_signals(limit=1000)
        assert len(signals) > 0
        assert all(s.get("is_demo") is True for s in signals)

    def test_seed_demo_heat_events_tagged_is_demo(self):
        engine = ConvergenceEngine(seed_demo=True)
        heat_events = engine.get_heat_events()
        assert len(heat_events) > 0
        assert all(h.get("is_demo") is True for h in heat_events)

    def test_stats_demo_counts_match_real_counts_are_zero(self):
        engine = ConvergenceEngine(seed_demo=True)
        stats = engine.stats()
        assert stats["demo_signals"] == stats["total_signals"]
        assert stats["real_signals"] == 0
        assert stats["demo_heat_events"] == stats["heat_events"]
        assert stats["real_heat_events"] == 0


class TestRealSignalsViaAddSignals:
    """Mirrors how AutonomousScanner feeds real EDGAR signals in."""

    def test_add_signals_tags_as_real_by_default(self):
        engine = ConvergenceEngine()
        engine.add_signals([
            {"id": "edgar-1", "type": "equity_raise", "entity": "Real Co LLC",
             "location": "TX, US", "date": "2026-07-01T00:00:00Z",
             "details": "SEC Form D filed", "state": "TX"},
        ])
        signals = engine.get_signals()
        assert len(signals) == 1
        assert signals[0]["is_demo"] is False

    def test_real_signals_can_produce_real_heat_events(self):
        engine = ConvergenceEngine()
        engine.add_signals([
            {"id": "e1", "type": "llc_formation", "entity": "Assembly Co LLC",
             "location": "TX, US", "date": "2026-07-01T00:00:00Z",
             "details": "New LLC formed", "state": "TX"},
            {"id": "e2", "type": "land_purchase", "entity": "Assembly Co LLC",
             "location": "TX, US", "date": "2026-07-05T00:00:00Z",
             "details": "Land acquired", "state": "TX"},
        ])
        heat = engine.get_heat_events()
        assert len(heat) == 1
        assert heat[0]["is_demo"] is False

    def test_mixing_real_and_demo_does_not_mislabel_real_heat_as_demo(self):
        engine = ConvergenceEngine(seed_demo=True)
        pre_count = len(engine.get_heat_events())
        engine.add_signals([
            {"id": "e1", "type": "llc_formation", "entity": "Assembly Co LLC",
             "location": "TX, US", "date": "2026-07-01T00:00:00Z",
             "details": "New LLC formed", "state": "TX"},
            {"id": "e2", "type": "land_purchase", "entity": "Assembly Co LLC",
             "location": "TX, US", "date": "2026-07-05T00:00:00Z",
             "details": "Land acquired", "state": "TX"},
        ])
        heat = engine.get_heat_events()
        assert len(heat) == pre_count + 1
        real_events = [h for h in heat if not h["is_demo"]]
        assert len(real_events) == 1
        assert real_events[0]["entity"] == "Assembly Co LLC"
