"""Tests for routes/eagleeye.py::cre_heatmap — must be grounded in real
SignalEngine signals across all asset classes, not a Claude free-invention
that falls back to the same narrow, senior-living-heavy static list."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from routes.eagleeye import _build_cre_heatmap_from_real_signals, _CRE_FALLBACK_PROPERTIES


class TestBuildHeatmapFromRealSignals:
    def test_aggregates_by_state(self):
        signals = [
            {"entity": "A Corp", "state": "TX", "sector": "industrial", "nest_score": 0.8,
             "snippet": "Industrial signal", "trigger_event": "comparable_filing"},
            {"entity": "B Corp", "state": "TX", "sector": "retail", "nest_score": 0.5,
             "snippet": "Retail signal", "trigger_event": "comparable_filing"},
            {"entity": "C Corp", "state": "FL", "sector": "hospitals", "nest_score": 0.9,
             "snippet": "Hospital signal", "trigger_event": "comparable_filing"},
        ]
        states, properties = _build_cre_heatmap_from_real_signals(signals)
        state_codes = {s["state"] for s in states}
        assert state_codes == {"TX", "FL"}
        tx = next(s for s in states if s["state"] == "TX")
        assert tx["signal_count"] == 2
        assert set(tx["deal_types"]) == {"industrial", "retail"}

    def test_top_properties_include_real_entity_names_only(self):
        signals = [
            {"entity": "Real Entity LLC", "state": "CA", "sector": "office", "nest_score": 0.7,
             "snippet": "Office filing", "trigger_event": "comparable_filing", "edgar_url": "https://x"},
        ]
        states, properties = _build_cre_heatmap_from_real_signals(signals)
        assert properties[0]["name"] == "Real Entity LLC"
        # No fabricated dollar figures for data EDGAR text signals don't carry
        assert properties[0]["loan_amount_usd"] is None
        assert properties[0]["estimated_noi_usd"] is None

    def test_empty_signals_produce_empty_output_not_fabricated_data(self):
        states, properties = _build_cre_heatmap_from_real_signals([])
        assert states == []
        assert properties == []

    def test_covers_asset_classes_beyond_senior_living(self):
        signals = [
            {"entity": "Industrial Co", "state": "TX", "sector": "industrial", "nest_score": 0.6,
             "snippet": "", "trigger_event": "comparable_filing"},
            {"entity": "Retail Co", "state": "GA", "sector": "retail", "nest_score": 0.6,
             "snippet": "", "trigger_event": "comparable_filing"},
            {"entity": "Office Co", "state": "NY", "sector": "office", "nest_score": 0.6,
             "snippet": "", "trigger_event": "comparable_filing"},
        ]
        _, properties = _build_cre_heatmap_from_real_signals(signals)
        asset_types = {p["asset_type"] for p in properties}
        assert asset_types == {"industrial", "retail", "office"}


class TestCreHeatmapRoute:
    def test_uses_real_signals_when_available(self, client, monkeypatch):
        import routes.eagleeye as eagleeye_module

        class _FakeEngine:
            def run_signal_pipeline(self, max_signals=200, sectors=None):
                return {"signals": [
                    {"entity": "Real Office Co", "state": "NY", "sector": "office",
                     "nest_score": 0.75, "desk": "cre", "snippet": "Real filing",
                     "trigger_event": "comparable_filing"},
                ]}

        monkeypatch.setattr("services.signal_engine.SignalEngine", _FakeEngine)
        eagleeye_module._cre_cache.clear()

        resp = client.get("/api/eagleeye/cre-heatmap")
        data = resp.get_json()["data"]
        assert data["source"] == "real_signals"
        names = {p["name"] for p in data["top_properties"]}
        assert "Real Office Co" in names
        assert "Jacaranda Trace Senior Living" not in names

    def test_falls_back_when_no_real_signals(self, client, monkeypatch):
        import routes.eagleeye as eagleeye_module

        class _EmptyEngine:
            def run_signal_pipeline(self, max_signals=200, sectors=None):
                return {"signals": []}

        monkeypatch.setattr("services.signal_engine.SignalEngine", _EmptyEngine)
        eagleeye_module._cre_cache.clear()

        resp = client.get("/api/eagleeye/cre-heatmap")
        data = resp.get_json()["data"]
        assert data["source"] == "fallback"
        assert data["top_properties"] == _CRE_FALLBACK_PROPERTIES
