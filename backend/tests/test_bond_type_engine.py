"""Tests for bond_type_engine — tax-exempt eligibility and option generation."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.bond_type_engine import generate_all_bond_options, BondType


TAX_EXEMPT_TYPES = {
    BondType.REVENUE_BOND.value,
    BondType.DUAL_TRANCHE_NEST.value,
    BondType.TAX_EXEMPT_PAB.value,
}


class TestGovernmentalBorrowerEligibility:
    """Ticket 1: governmental/municipal borrowers must get tax-exempt options.

    Regression for the bug where only nonprofit/501c3 borrower_type values
    unlocked tax-exempt bond types, leaving every governmental/municipal/
    conduit borrower with zero tax-exempt options.
    """

    BASE_DEAL = {
        "noi": 5_000_000,
        "dscr": 1.6,
        "ltv": 65,
        "bond_face": 10_000_000,
        "naics_code": "9999",  # deliberately not in the sector carve-outs
    }

    def _bond_types_for(self, borrower_type: str) -> set:
        deal = dict(self.BASE_DEAL, borrower_type=borrower_type)
        result = generate_all_bond_options(deal)
        return {opt["bond_type"] for opt in result["all_options"]}

    def test_governmental_borrower_gets_tax_exempt_options(self):
        assert self._bond_types_for("governmental") & TAX_EXEMPT_TYPES

    def test_municipality_borrower_gets_tax_exempt_options(self):
        assert self._bond_types_for("municipality") & TAX_EXEMPT_TYPES

    def test_municipal_borrower_gets_tax_exempt_options(self):
        assert self._bond_types_for("municipal") & TAX_EXEMPT_TYPES

    def test_issuer_borrower_gets_tax_exempt_options(self):
        assert self._bond_types_for("issuer") & TAX_EXEMPT_TYPES

    def test_conduit_borrower_gets_tax_exempt_options(self):
        assert self._bond_types_for("conduit") & TAX_EXEMPT_TYPES

    def test_nonprofit_borrower_still_gets_tax_exempt_options(self):
        """Original nonprofit eligibility must not regress."""
        assert self._bond_types_for("nonprofit") & TAX_EXEMPT_TYPES

    def test_for_profit_borrower_still_excluded(self):
        """Sanity: a plain for-profit, non-sector-matching borrower stays ineligible."""
        assert not (self._bond_types_for("for-profit corporation") & TAX_EXEMPT_TYPES)
