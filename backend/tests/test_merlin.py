"""Tests for MerlinAgent.scan_edgar_for_targets — Ticket 18: real EDGAR
scanning via SignalEngine, fabricated data only ever opt-in and tagged."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import agents.merlin as merlin_module
from agents.merlin import MerlinAgent

merlin = MerlinAgent()


class _FakeSignalEngine:
    def __init__(self, results=None):
        self._results = results if results is not None else []

    def scan_edgar_ma_targets(self, naics_codes=None):
        return self._results


class TestScanEdgarForTargets:
    def test_no_targets_and_no_synthetic_by_default(self, monkeypatch):
        monkeypatch.setattr(merlin_module, "_signal_engine", _FakeSignalEngine(results=[]))
        result = merlin.scan_edgar_for_targets(naics_codes=["623110"])
        assert result["targets"] == []
        assert result["targets_found"] == 0
        assert result["is_demo_data"] is False

    def test_real_signal_engine_results_are_used_and_not_flagged_demo(self, monkeypatch):
        fake = _FakeSignalEngine(results=[{
            "entity": "Real Target Corp", "naics_hint": "623110",
            "form_type": "10-K", "filing_date": "2026-06-01",
            "edgar_url": "https://example.com",
        }])
        monkeypatch.setattr(merlin_module, "_signal_engine", fake)
        result = merlin.scan_edgar_for_targets(naics_codes=["623110"])
        assert result["targets_found"] == 1
        assert result["targets"][0]["name"] == "Real Target Corp"
        assert result["targets"][0]["is_demo"] is False
        assert result["is_demo_data"] is False

    def test_synthetic_data_requires_explicit_opt_in(self, monkeypatch):
        monkeypatch.setattr(merlin_module, "_signal_engine", _FakeSignalEngine(results=[]))
        no_synthetic = merlin.scan_edgar_for_targets(naics_codes=["623110"], allow_synthetic=False)
        with_synthetic = merlin.scan_edgar_for_targets(naics_codes=["623110"], allow_synthetic=True)
        assert no_synthetic["targets"] == []
        assert with_synthetic["targets_found"] > 0
        assert all(t["is_demo"] for t in with_synthetic["targets"])
        assert with_synthetic["is_demo_data"] is True

    def test_real_results_take_priority_over_synthetic_even_when_allowed(self, monkeypatch):
        fake = _FakeSignalEngine(results=[{
            "entity": "Real Target Corp", "naics_hint": "623110",
            "form_type": "10-K", "filing_date": "2026-06-01", "edgar_url": "",
        }])
        monkeypatch.setattr(merlin_module, "_signal_engine", fake)
        result = merlin.scan_edgar_for_targets(naics_codes=["623110"], allow_synthetic=True)
        assert result["targets_found"] == 1
        assert result["targets"][0]["is_demo"] is False
