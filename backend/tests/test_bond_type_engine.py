"""Tests for bond_type_engine — tax-exempt eligibility and option generation."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.bond_type_engine import generate_all_bond_options, BondType, PAR_VALUES


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


class TestBanAndMezzanineReachability:
    """Ticket 2: BAN and Mezzanine must actually be reachable outputs.

    Regression for the bug where BAN required dscr < 1.30 (below the 1.35
    default used when no dscr is supplied — structurally unreachable) and
    Mezzanine required ltv > 78 (above every real profile tested). Neither
    ever fired despite bond_intelligence recommending BAN as an achievable
    option and Horn Lake carrying a real $12M mezzanine tranche.
    """

    def _bond_types_for(self, **overrides) -> set:
        deal = {
            "noi": 5_000_000, "dscr": 1.6, "ltv": 65,
            "bond_face": 10_000_000, "naics_code": "9999",
        }
        deal.update(overrides)
        result = generate_all_bond_options(deal)
        return {opt["bond_type"] for opt in result["all_options"]}

    def test_pre_development_stage_gets_ban(self):
        """Aligns with bond_intelligence.get_financing_path('pre_development', ...)."""
        types = self._bond_types_for(stage="pre_development", dscr=1.8, ltv=60)
        assert BondType.BAN.value in types

    def test_sub_bbb_minus_dscr_gets_ban(self):
        """Aligns with bond_intelligence.assess_rating_readiness()'s unconditional
        'BAN (unrated, QIB only)' fallback below the BBB- dscr floor (1.5x)."""
        types = self._bond_types_for(dscr=1.40, ltv=65)
        assert BondType.BAN.value in types

    def test_strong_stabilized_deal_does_not_get_ban(self):
        types = self._bond_types_for(dscr=1.8, ltv=60)
        assert BondType.BAN.value not in types

    def test_ltv_above_bbb_minus_ceiling_gets_mezzanine(self):
        """Aligns with bond_intelligence's BBB- ltv ceiling of 70%."""
        types = self._bond_types_for(dscr=1.8, ltv=75)
        assert BondType.MEZZANINE.value in types

    def test_horn_lake_like_profile_gets_mezzanine(self):
        """Horn Lake carries a real $12M mezzanine tranche despite a
        blended DSCR at/above 1.5x — the LTV gap is what drives it."""
        types = self._bond_types_for(dscr=1.55, ltv=76, bond_face=100_000_000)
        assert BondType.MEZZANINE.value in types


class TestParSizing:
    """Ticket 3: par sizing must reflect the actual requested amount, not
    just snap to the fixed 25/50/75/100/150/200/250/500M ladder.

    Regression for the bug where a requested amount below the ladder's
    floor ($25M) — like the real $10.0M bank-qualified size that saved
    ~$470K on 2027A — produced zero band matches and fell through to
    whichever ladder rung happened to survive the 0.40x-2.50x filter.
    """

    def _par_values_for(self, bond_face: float) -> set:
        deal = {
            "noi": 800_000, "dscr": 1.6, "ltv": 65,
            "bond_face": bond_face, "naics_code": "9999",
            "borrower_type": "governmental",
        }
        result = generate_all_bond_options(deal)
        return {opt["par_value"] for opt in result["all_options"]}

    def test_10m_bank_qualified_size_is_producible(self):
        assert 10_000_000 in self._par_values_for(10_000_000)

    def test_small_request_does_not_snap_to_ladder_floor(self):
        pars = self._par_values_for(10_000_000)
        assert all(p <= 25_000_000 for p in pars if p != 25_000_000) or len(pars) > 1
        assert min(pars) < 25_000_000

    def test_no_requested_amount_falls_back_to_standard_ladder(self):
        assert self._par_values_for(0) == set(PAR_VALUES)

    def test_large_request_still_bounded_reasonably(self):
        pars = self._par_values_for(200_000_000)
        assert 200_000_000 in pars
        assert all(80_000_000 <= p <= 500_000_000 for p in pars)
