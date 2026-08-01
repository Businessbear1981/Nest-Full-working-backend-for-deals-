"""Tests for bond_type_engine — tax-exempt eligibility and option generation."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.bond_type_engine import (
    generate_all_bond_options, BondType, PAR_VALUES,
    resolve_sector, REVENUE_SECTOR_REGISTRY,
    calculate_coupon, AmortizationType,
    BRIDGE_TO_PERMANENT_CONVERSION_TRIGGERS,
    generate_amortization_schedule,
)


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


class TestSectorResolution:
    """Ticket 20 / 19: NAICS -> sector resolution."""

    def test_exact_naics_match(self):
        assert resolve_sector("221310") == "water_sewer"  # water supply
        assert resolve_sector("721110") == "hotels_hospitality"  # hotels

    def test_4digit_prefix_fallback(self):
        # 622110 is exact hospitals; a sibling code under the same 4-digit
        # family should still resolve even without an exact entry.
        assert resolve_sector("622199") == "hospitals"

    def test_unmapped_naics_returns_none(self):
        assert resolve_sector("999999") is None

    def test_empty_naics_returns_none(self):
        assert resolve_sector("") is None
        assert resolve_sector(None) is None


class TestSectorAwareSuitabilityScore:
    """Ticket 20: suitability_score must reflect real sector fit, not just
    DSCR-optimal mechanics — the bug where every sector (water/sewer,
    hospitality, sports facility, etc.) returned the identical top
    recommendation regardless of NAICS code."""

    def _top_rec_for(self, naics_code: str, borrower_type: str = "") -> dict:
        deal = {
            "noi": 5_000_000, "dscr": 1.6, "ltv": 65,
            "bond_face": 50_000_000, "naics_code": naics_code,
            "borrower_type": borrower_type,
        }
        result = generate_all_bond_options(deal)
        return result["recommendations"][0]

    def test_different_sectors_produce_different_top_recommendations(self):
        water_top = self._top_rec_for("221310", borrower_type="governmental")  # water/sewer
        hotel_top = self._top_rec_for("721110")  # hospitality

        assert water_top["sector"] == "water_sewer"
        assert hotel_top["sector"] == "hotels_hospitality"
        assert water_top["bond_type"] != hotel_top["bond_type"]

    def test_recommended_bond_type_is_a_real_sector_fit(self):
        water_top = self._top_rec_for("221310", borrower_type="governmental")
        fit_types = {bt.value for bt in REVENUE_SECTOR_REGISTRY["water_sewer"]["fit_bond_types"]}
        assert water_top["bond_type"] in fit_types
        assert water_top["sector_validated"] is True

    def test_options_are_tagged_sector_validated_when_sector_known(self):
        deal = {"noi": 5_000_000, "dscr": 1.6, "ltv": 65, "bond_face": 50_000_000, "naics_code": "221310", "borrower_type": "governmental"}
        result = generate_all_bond_options(deal)
        assert all(opt["sector_validated"] for opt in result["all_options"])

    def test_unmapped_sector_falls_back_to_dscr_optimal_and_is_flagged(self):
        deal = {"noi": 5_000_000, "dscr": 1.6, "ltv": 65, "bond_face": 50_000_000, "naics_code": "999999"}
        result = generate_all_bond_options(deal)
        assert all(not opt["sector_validated"] for opt in result["all_options"])

    def test_explicit_sector_key_overrides_naics_resolution(self):
        deal = {
            "noi": 5_000_000, "dscr": 1.6, "ltv": 65, "bond_face": 50_000_000,
            "naics_code": "999999", "sector": "toll_roads",
        }
        result = generate_all_bond_options(deal)
        assert result["recommendations"][0]["sector"] == "toll_roads"
        assert result["recommendations"][0]["sector_validated"] is True


class TestTicket21NewBondTypes:
    """Ticket 21: Housing Authority, GAN/RAN/TAN, VRDO, Bridge-to-Permanent
    must be real, reachable options with correct structural metadata —
    not enum-only stubs."""

    BASE_DEAL = {
        "noi": 3_000_000, "dscr": 1.3, "ltv": 65, "bond_face": 40_000_000,
        "naics_code": "531110", "borrower_type": "governmental",
        "anticipated_grant_award": True,
    }

    def _options_for(self, **overrides) -> list:
        deal = dict(self.BASE_DEAL, **overrides)
        return generate_all_bond_options(deal)["all_options"]

    def test_housing_authority_reachable_for_housing_naics(self):
        types = {o["bond_type"] for o in self._options_for()}
        assert BondType.HOUSING_AUTHORITY.value in types

    def test_gan_reachable_when_grant_award_anticipated(self):
        types = {o["bond_type"] for o in self._options_for(anticipated_grant_award=True)}
        assert BondType.GAN.value in types

    def test_gan_unreachable_without_grant_award(self):
        types = {o["bond_type"] for o in self._options_for(anticipated_grant_award=False)}
        assert BondType.GAN.value not in types

    def test_ran_reachable_for_nonprofit_below_dscr_ceiling(self):
        types = {o["bond_type"] for o in self._options_for(dscr=1.4)}
        assert BondType.RAN.value in types

    def test_tan_requires_actual_taxing_authority_not_just_any_nonprofit(self):
        gov_types = {o["bond_type"] for o in self._options_for(borrower_type="governmental")}
        nonprofit_types = {o["bond_type"] for o in self._options_for(borrower_type="nonprofit")}
        assert BondType.TAN.value in gov_types
        assert BondType.TAN.value not in nonprofit_types

    def test_vrdo_reachable_and_flagged_variable_rate(self):
        options = [o for o in self._options_for() if o["bond_type"] == BondType.VRDO.value]
        assert options
        assert all(o["rate_type"] == "variable" for o in options)

    def test_vrdo_unreachable_below_liquidity_facility_threshold(self):
        types = {o["bond_type"] for o in self._options_for(bond_face=2_000_000)}
        assert BondType.VRDO.value not in types

    def test_fixed_rate_types_flagged_fixed(self):
        options = [o for o in self._options_for() if o["bond_type"] == BondType.REVENUE_BOND.value]
        assert options
        assert all(o["rate_type"] == "fixed" for o in options)

    def test_anticipation_notes_carry_real_repayment_source(self):
        options = self._options_for()
        gan = next(o for o in options if o["bond_type"] == BondType.GAN.value)
        ran = next(o for o in options if o["bond_type"] == BondType.RAN.value)
        tan = next(o for o in options if o["bond_type"] == BondType.TAN.value)
        assert gan["anticipated_repayment_source"] == "grant_award"
        assert ran["anticipated_repayment_source"] == "pledged_revenue"
        assert tan["anticipated_repayment_source"] == "property_tax_levy"

    def test_anticipation_notes_are_short_term(self):
        options = self._options_for()
        for bt_value, max_years in [
            (BondType.GAN.value, 2), (BondType.RAN.value, 1), (BondType.TAN.value, 1),
        ]:
            matches = [o for o in options if o["bond_type"] == bt_value]
            assert matches
            assert all(o["maturity_years"] <= max_years for o in matches)

    def test_bridge_to_permanent_reachable_pre_stabilization(self):
        types = {o["bond_type"] for o in self._options_for(dscr=1.4)}
        assert BondType.BRIDGE_TO_PERMANENT.value in types

    def test_bridge_to_permanent_unreachable_once_stabilized(self):
        types = {o["bond_type"] for o in self._options_for(dscr=2.0)}
        assert BondType.BRIDGE_TO_PERMANENT.value not in types

    def test_bridge_to_permanent_carries_real_conversion_triggers(self):
        options = self._options_for(dscr=1.4)
        bridge = next(o for o in options if o["bond_type"] == BondType.BRIDGE_TO_PERMANENT.value)
        assert bridge["bridge_conversion_triggers"] == BRIDGE_TO_PERMANENT_CONVERSION_TRIGGERS
        assert bridge["maturity_years"] == 3

    def test_vrdo_coupon_uses_sifma_index_when_supplied(self):
        no_index = calculate_coupon(BondType.VRDO, AmortizationType.LEVEL_DEBT_SERVICE, dscr=1.5, ltv=65)
        with_index = calculate_coupon(BondType.VRDO, AmortizationType.LEVEL_DEBT_SERVICE, dscr=1.5, ltv=65, sifma_index_bps=350)
        assert no_index != with_index
        assert with_index == round(350 / 100.0 + 0.15, 2)


class TestCabAccretion:
    """Ticket 19: real CAB (Capital Appreciation Bond) accretion math —
    semiannual compounding, zero cash debt service until maturity, full
    accreted value due as a lump sum at maturity. Previously the concept
    was only described in comments (bond_intelligence.py's BAN description)
    but never actually computed anywhere in the codebase."""

    def test_maturity_value_matches_standard_semiannual_compounding_formula(self):
        schedule = generate_amortization_schedule(
            par=10_000_000, coupon_pct=6.0, maturity_years=5,
            amort_type=AmortizationType.CAB_ACCRETION,
        )
        expected_maturity_value = 10_000_000 * (1 + 0.03) ** 10
        assert schedule[-1]["accreted_value"] == round(expected_maturity_value, 2)

    def test_zero_cash_debt_service_until_maturity(self):
        schedule = generate_amortization_schedule(
            par=10_000_000, coupon_pct=6.0, maturity_years=5,
            amort_type=AmortizationType.CAB_ACCRETION,
        )
        for row in schedule[:-1]:
            assert row["total_ds"] == 0.0
            assert row["principal"] == 0.0
        assert schedule[-1]["total_ds"] == schedule[-1]["accreted_value"]
        assert schedule[-1]["principal"] == 10_000_000

    def test_accreted_value_strictly_increasing(self):
        schedule = generate_amortization_schedule(
            par=10_000_000, coupon_pct=6.0, maturity_years=5,
            amort_type=AmortizationType.CAB_ACCRETION,
        )
        values = [row["accreted_value"] for row in schedule]
        assert values == sorted(values)
        assert len(set(values)) == len(values)

    def test_cab_reachable_as_a_real_amortization_option(self):
        deal = {
            "noi": 3_000_000, "dscr": 1.3, "ltv": 65, "bond_face": 40_000_000,
            "naics_code": "531110", "borrower_type": "governmental",
        }
        result = generate_all_bond_options(deal)
        cab_options = [o for o in result["all_options"] if o["amortization"] == AmortizationType.CAB_ACCRETION.value]
        assert cab_options
