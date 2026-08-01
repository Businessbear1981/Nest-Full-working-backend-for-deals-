"""Tests for counterparty_db — real bond insurance mechanics (Ticket 19)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.counterparty_db import (
    bond_insurance_premium, BOND_INSURANCE_ACTIVE_WRITERS,
    BOND_INSURANCE_PREMIUM_PCT_RANGE,
)


class TestActiveWriters:
    def test_only_two_active_writers_with_real_market_share(self):
        assert len(BOND_INSURANCE_ACTIVE_WRITERS) == 2
        names = {w["name"] for w in BOND_INSURANCE_ACTIVE_WRITERS}
        assert "Assured Guaranty (AGM)" in names
        assert "Build America Mutual (BAM)" in names

    def test_market_shares_sum_to_100(self):
        total = sum(w["market_share_pct"] for w in BOND_INSURANCE_ACTIVE_WRITERS)
        assert total == 100

    def test_berkshire_not_counted_as_active_writer(self):
        names = {w["name"] for w in BOND_INSURANCE_ACTIVE_WRITERS}
        assert "Berkshire Hathaway Assurance" not in names


class TestBondInsurancePremium:
    def test_priced_off_total_debt_service_within_real_range(self):
        result = bond_insurance_premium(total_debt_service=50_000_000, credit_quality="average")
        assert BOND_INSURANCE_PREMIUM_PCT_RANGE["min"] <= result["premium_pct_of_total_debt_service"] <= BOND_INSURANCE_PREMIUM_PCT_RANGE["max"]
        assert result["premium_usd"] == round(50_000_000 * result["premium_pct_of_total_debt_service"] / 100.0)

    def test_strong_credit_prices_at_low_end(self):
        result = bond_insurance_premium(total_debt_service=50_000_000, credit_quality="strong")
        assert result["premium_pct_of_total_debt_service"] == BOND_INSURANCE_PREMIUM_PCT_RANGE["min"]

    def test_weak_credit_prices_at_high_end(self):
        result = bond_insurance_premium(total_debt_service=50_000_000, credit_quality="weak")
        assert result["premium_pct_of_total_debt_service"] == BOND_INSURANCE_PREMIUM_PCT_RANGE["max"]

    def test_output_includes_real_active_writers(self):
        result = bond_insurance_premium(total_debt_service=50_000_000)
        assert len(result["active_writers"]) == 2
