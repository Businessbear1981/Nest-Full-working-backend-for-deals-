"""Tests for SignalEngine — Ticket 18 consolidation: EagleEyeScanner's real
FRED/sector-comparable/maturity-wall coverage merged in as the qualified,
routed base of the scanning cluster."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.signal_engine import SignalEngine, _SECTOR_COMPARABLE_TERMS

engine = SignalEngine()


class TestMaturityWall:
    def test_returns_real_aggregate_figures(self):
        wall = engine.scan_maturity_wall()
        assert wall["total_maturities_2026"] == 162_100_000_000
        assert wall["total_maturities_2027"] == 167_700_000_000
        assert wall["multifamily_share"] == 0.33

    def test_austin_market_adds_real_market_detail(self):
        wall = engine.scan_maturity_wall(market="Austin")
        assert wall["market"] == "Austin, TX"
        assert wall["vacancy_rate"] == 0.142
        assert len(wall["distressed_signals"]) == 3

    def test_unknown_market_falls_back_to_aggregate_only(self):
        wall = engine.scan_maturity_wall(market="Nowhere, ZZ")
        assert "market" not in wall
        assert wall["distressed_signals"] == []


class TestFredMarketContext:
    def test_returns_empty_dict_without_api_key(self, monkeypatch):
        monkeypatch.delenv("FRED_API_KEY", raising=False)
        result = engine.get_fred_market_context()
        assert result == {}


class TestSectorComparableQualification:
    """Sector-comparable signals must actually flow through real
    qualification, not fall through to the generic COLD/0.0 default the
    way unscored EagleEyeScanner data used to."""

    def test_s11_in_hot_state_recent_scores_hot(self):
        signal = {
            "signal_type": "sector_comparable",
            "entity": "Test Senior Living REIT",
            "filing_date": "2026-06-01",
            "form_type": "S-11",
            "state": "TX",
            "sector": "senior_living",
            "trigger_event": "comparable_filing",
            "raw_score": 0.0,
        }
        result = engine.qualify_signals([signal])[0]
        assert result["nest_score"] > 0
        assert result["grade"] in ("HOT", "WARM")
        assert result["desk"] == "cre"
        assert result["qualified"] is True

    def test_old_filing_cold_state_scores_lower_than_hot_case(self):
        hot = engine.qualify_signals([{
            "signal_type": "sector_comparable", "entity": "A", "filing_date": "2026-06-01",
            "form_type": "S-11", "state": "TX", "sector": "senior_living",
            "trigger_event": "comparable_filing", "raw_score": 0.0,
        }])[0]
        cold = engine.qualify_signals([{
            "signal_type": "sector_comparable", "entity": "B", "filing_date": "2015-01-01",
            "form_type": "8-K", "state": "ND", "sector": "unknown_sector",
            "trigger_event": "comparable_filing", "raw_score": 0.0,
        }])[0]
        assert hot["nest_score"] > cold["nest_score"]

    def test_sector_comparable_types_are_real_registered_sectors(self):
        assert "senior_living" in _SECTOR_COMPARABLE_TERMS
        assert "healthcare" in _SECTOR_COMPARABLE_TERMS


class TestRunSignalPipelineBackwardCompatible:
    def test_no_sectors_arg_does_not_call_sector_comparables(self, monkeypatch):
        called = []
        monkeypatch.setattr(engine, "scan_sector_comparables", lambda *a, **k: called.append(1) or [])
        monkeypatch.setattr(engine, "scan_edgar_ma_targets", lambda *a, **k: [])
        monkeypatch.setattr(engine, "scan_edgar_cre_events", lambda *a, **k: [])
        monkeypatch.setattr(engine, "scan_construction_permits", lambda *a, **k: [])
        engine.run_signal_pipeline()
        assert called == []

    def test_sectors_arg_pulls_comparables_for_each_sector(self, monkeypatch):
        calls = []
        monkeypatch.setattr(engine, "scan_sector_comparables", lambda sector, **k: calls.append(sector) or [])
        monkeypatch.setattr(engine, "scan_edgar_ma_targets", lambda *a, **k: [])
        monkeypatch.setattr(engine, "scan_edgar_cre_events", lambda *a, **k: [])
        monkeypatch.setattr(engine, "scan_construction_permits", lambda *a, **k: [])
        engine.run_signal_pipeline(sectors=["senior_living", "healthcare"])
        assert calls == ["senior_living", "healthcare"]
