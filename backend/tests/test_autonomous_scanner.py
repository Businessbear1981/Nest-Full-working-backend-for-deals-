"""Tests for AutonomousScanner — Ticket 18: EDGAR scanning delegates to
SignalEngine instead of maintaining a separate httpx client."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.autonomous_scanner import AutonomousScanner
from services.signal_engine import SignalEngine


class _FakeSignalEngine:
    def __init__(self, ma_signals=None, cre_signals=None):
        self._ma = ma_signals or []
        self._cre = cre_signals or []
        self.calls = []

    def scan_edgar_ma_targets(self):
        self.calls.append("ma")
        return self._ma

    def scan_edgar_cre_events(self):
        self.calls.append("cre")
        return self._cre


class TestEdgarScanDelegatesToSignalEngine:
    def test_calls_both_real_scan_methods(self):
        fake = _FakeSignalEngine()
        scanner = AutonomousScanner(signal_engine=fake)
        scanner._scan_edgar()
        assert "ma" in fake.calls
        assert "cre" in fake.calls

    def test_normalizes_signal_engine_output_shape(self):
        fake = _FakeSignalEngine(ma_signals=[{
            "signal_type": "ma_target", "entity": "Test Corp", "filing_date": "2026-06-01",
            "form_type": "8-K", "state": "TX", "trigger_event": "merger_agreement",
            "edgar_url": "https://example.com", "snippet": "Merger agreement filed", "raw_score": 0.0,
        }])
        scanner = AutonomousScanner(signal_engine=fake)
        signals = scanner._scan_edgar()
        assert len(signals) == 1
        sig = signals[0]
        assert sig["entity"] == "Test Corp"
        assert sig["type"] == "merger_agreement"
        assert sig["source"] == "SEC EDGAR"
        assert sig["state"] == "TX"
        assert "id" in sig and "date" in sig and "details" in sig

    def test_default_constructor_uses_real_signal_engine(self):
        scanner = AutonomousScanner()
        assert isinstance(scanner._signals, SignalEngine)

    def test_edgar_error_does_not_raise(self):
        class _Broken:
            def scan_edgar_ma_targets(self):
                raise RuntimeError("boom")
            def scan_edgar_cre_events(self):
                return []
        scanner = AutonomousScanner(signal_engine=_Broken())
        signals = scanner._scan_edgar()
        assert signals == []
