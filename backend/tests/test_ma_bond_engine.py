"""Tests for MABondEngine — PIK vs. cash-pay modeling."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.ma_bond_engine import MABondEngine

engine = MABondEngine()


class TestPikVsCashPay:
    """explanation must match the computed verdict, not a hardcoded PIK-favoring string."""

    def test_high_growth_pik_wins_and_explanation_matches(self):
        r = engine.model_pik_vs_cash_pay(
            bond_amount=50_000_000, coupon_pct=11.0, hold_years=5, ebitda_growth_pct=30,
        )
        assert r["verdict"] == "PIK wins"
        assert "pik" in r["explanation"].lower()
        assert "cash pay wins" not in r["explanation"].lower()

    def test_low_growth_cash_pay_wins_and_explanation_matches(self):
        r = engine.model_pik_vs_cash_pay(
            bond_amount=50_000_000, coupon_pct=11.0, hold_years=5, ebitda_growth_pct=2,
        )
        assert r["verdict"] == "Cash pay wins"
        assert "cash pay" in r["explanation"].lower()
        assert "pik wins for growth companies every time" not in r["explanation"].lower()

    def test_explanation_never_contradicts_verdict(self):
        for growth in (2, 8, 15, 22, 30):
            r = engine.model_pik_vs_cash_pay(
                bond_amount=50_000_000, coupon_pct=11.0, hold_years=5, ebitda_growth_pct=growth,
            )
            if r["verdict"] == "PIK wins":
                assert "cash pay wins" not in r["explanation"].lower()
            else:
                assert "pik wins for growth companies every time" not in r["explanation"].lower()
