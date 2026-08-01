"""Tests for rating_benchmarks — real DSRF sizing (Ticket 19)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.rating_benchmarks import dsrf_size, get_structuring_targets


class TestDsrfSize:
    """Real implementation of the IRC 148(d) safe harbor already documented
    as text in STRUCTURING_CRITERIA['dsrf_sizing']: least of MADS, 125% of
    AADS, or 10% of par."""

    def test_mads_is_binding(self):
        result = dsrf_size(mads=5_000_000, aads=3_000_000, par=100_000_000)
        # 125% AADS = 3.75M, 10% par = 10M, MADS = 5M -> MADS is smallest? No: 3.75M < 5M
        assert result["binding_constraint"] == "125pct_aads"
        assert result["dsrf_required"] == 3_750_000

    def test_10pct_par_is_binding_for_small_par(self):
        result = dsrf_size(mads=5_000_000, aads=4_500_000, par=20_000_000)
        # 125% AADS = 5.625M, 10% par = 2M, MADS = 5M -> 10% par smallest
        assert result["binding_constraint"] == "10pct_par"
        assert result["dsrf_required"] == 2_000_000

    def test_mads_is_binding_when_smallest(self):
        result = dsrf_size(mads=1_000_000, aads=900_000, par=50_000_000)
        # 125% AADS = 1.125M, 10% par = 5M, MADS = 1M -> MADS smallest
        assert result["binding_constraint"] == "mads"
        assert result["dsrf_required"] == 1_000_000

    def test_all_three_candidates_reported(self):
        result = dsrf_size(mads=5_000_000, aads=3_000_000, par=100_000_000)
        assert set(result["candidates"].keys()) == {"mads", "125pct_aads", "10pct_par"}


class TestGetStructuringTargets:
    def test_a_grade_targets_match_real_thresholds(self):
        targets = get_structuring_targets("A")
        assert targets["min_dscr"] == 1.50
        assert targets["min_equity"] == 0.30
