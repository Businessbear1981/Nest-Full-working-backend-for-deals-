"""Tests for EagleEyeScanner.scan_for_equity_partners — Ticket 11."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.eagleeye_scanner import EagleEyeScanner

scanner = EagleEyeScanner()


class TestScanForEquityPartners:
    def test_no_gap_returns_no_gap_result(self):
        deal = {"id": "deal-1", "sources_and_uses": {"has_equity_gap": False, "equity_gap_usd": 0}}
        result = scanner.scan_for_equity_partners(deal)
        assert result["has_equity_gap"] is False
        assert result["matched_partners"] == []

    def test_real_gap_reports_gap_without_fabricating_partners(self):
        deal = {
            "id": "deal-2",
            "sources_and_uses": {"has_equity_gap": True, "equity_gap_usd": 21_656_250},
        }
        result = scanner.scan_for_equity_partners(deal)
        assert result["has_equity_gap"] is True
        assert result["equity_gap_usd"] == 21_656_250
        # The core guarantee: no invented counterparty names, ever.
        assert result["matched_partners"] == []
        assert result["candidate_sourcing_status"] == "not_built"

    def test_output_does_not_contain_fictional_firm_names(self):
        """Regression against repeating the Hawkeye BUYER_UNIVERSE bug —
        this must never return fabricated equity-partner names."""
        deal = {"id": "deal-3", "sources_and_uses": {"has_equity_gap": True, "equity_gap_usd": 5_000_000}}
        result = scanner.scan_for_equity_partners(deal)
        assert len(result["matched_partners"]) == 0
