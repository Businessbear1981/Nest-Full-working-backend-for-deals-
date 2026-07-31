"""Tests for EMMAEngine — sector-aware static template fallback."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.emma_engine import EMMAEngine

engine = EMMAEngine()

# Sectors the ticket called out by name as incorrectly bucketed into
# corporate_ma's 7-10% high-yield band.
NAMED_SECTORS = ["water_sewer", "hotels_hospitality", "municipal"]

# Every sector SECTOR_NAICS_MAP claims to support, plus "corporate"/"other".
ALL_KNOWN_SECTORS = [
    "hospitals", "senior_living", "charter_schools", "higher_education",
    "affordable_multifamily", "market_rate_multifamily", "hotels_hospitality",
    "data_centers", "solid_waste", "water_sewer", "electric_power", "airports",
    "toll_roads", "manufacturing", "corporate",
]


class TestStaticTemplateSectorAwareness:
    """Ticket 4: template fallback must not return the same generic
    7-10% coupon band for every sector when the comp DB is empty."""

    def test_water_sewer_gets_investment_grade_muni_coupon(self):
        t = engine._static_template("water_sewer")["template"]
        assert t["coupon_range"]["max"] < 6.0
        assert t["typical_tax_status"] == "tax_exempt"

    def test_hotels_hospitality_distinct_from_water_sewer(self):
        water = engine._static_template("water_sewer")["template"]
        hotel = engine._static_template("hotels_hospitality")["template"]
        assert water["coupon_range"] != hotel["coupon_range"]
        assert water["typical_tax_status"] != hotel["typical_tax_status"]

    def test_municipal_does_not_use_corporate_band(self):
        municipal = engine._static_template("municipal")["template"]
        corporate = engine._static_template("corporate_ma")["template"]
        assert municipal["coupon_range"] != corporate["coupon_range"]
        assert municipal["coupon_range"]["max"] < 6.0

    def test_named_sectors_all_differ_from_corporate_ma_band(self):
        corporate_band = engine._static_template("corporate_ma")["template"]["coupon_range"]
        for sector in NAMED_SECTORS:
            band = engine._static_template(sector)["template"]["coupon_range"]
            assert band != corporate_band, f"{sector} still returns the corporate_ma band"

    def test_all_known_sectors_have_real_dedicated_entries(self):
        """Every sector SECTOR_NAICS_MAP claims to support must resolve to its
        own entry, not the shared unmapped-sector fallback."""
        for sector in ALL_KNOWN_SECTORS:
            result = engine._static_template(sector)
            assert result["source"] == "Operating Framework static defaults", (
                f"{sector} falls through to the generic default"
            )

    def test_truly_unmapped_sector_gets_conservative_muni_default_not_corporate(self):
        result = engine._static_template("some_totally_unmapped_sector")
        assert result["source"] == "generic municipal default (unmapped sector)"
        assert result["template"]["coupon_range"]["max"] < 6.0

    def test_corporate_alias_matches_corporate_ma(self):
        assert engine._static_template("corporate")["template"] == engine._static_template("corporate_ma")["template"]
