"""Tests for PhaseBondEngine — client-facing rationale must not cite NEST's
fee capture (Ticket 16)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.phase_bond_engine import PhaseBondEngine

engine = PhaseBondEngine()


class TestWhyPhaseBondsRationale:
    def test_why_phase_bonds_does_not_mention_fee_income(self):
        result = engine.structure_phase_bonds(tpc=100_000_000, base_rate_bps=650)
        rationale = result["why_phase_bonds"].lower()
        assert "fee" not in rationale
        assert "nest" not in rationale

    def test_why_phase_bonds_cites_real_structural_merits(self):
        result = engine.structure_phase_bonds(tpc=100_000_000, base_rate_bps=650)
        rationale = result["why_phase_bonds"].lower()
        assert "risk" in rationale
        assert "call" in rationale or "put" in rationale

    def test_fee_capture_language_moved_to_internal_note_only(self):
        result = engine.structure_phase_bonds(tpc=100_000_000, base_rate_bps=650)
        assert "why_phase_bonds" not in result["nest_economics"]
        assert "internal_note" in result["nest_economics"]

    def test_nest_economics_figures_still_computed(self):
        """The fix must not remove NEST's real internal economics data,
        only the client-facing fee-capture justification."""
        result = engine.structure_phase_bonds(tpc=100_000_000, base_rate_bps=650)
        econ = result["nest_economics"]
        assert econ["total_nest_fees_usd"] > 0
        assert econ["single_bond_fee_usd"] > 0


class TestComputeNestEconomicsExplanation:
    """The phase_bond_economics endpoint (routes/intelligence.py) returns
    this dict directly — its 'explanation' field had the same 'NEST earns
    2-3x more' framing as why_phase_bonds and is reachable the same way."""

    def test_explanation_field_renamed_and_not_framed_as_earnings_claim(self):
        structure = engine.structure_phase_bonds(tpc=100_000_000, base_rate_bps=650)
        econ = engine.compute_nest_economics(structure["phases"])
        assert "explanation" not in econ
        assert "internal_note" in econ
        assert "earns 2-3x more" not in econ["internal_note"].lower()

