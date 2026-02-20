"""Test SZZ quality metrics database module."""
import unittest

from varats.data.databases.szz_quality_metrics_database import (
    _calculate_szz_quality_score,
)
from varats.utils.git_util import CommitRepoPair


class TestSZZQualityMetricsDatabase(unittest.TestCase):
    """Test functions to create blame diff dependent databases."""

    def test_calculate_szz_quality_score_perfect_match(self) -> None:
        """Test SZZ quality score calculation."""
        commit_a = CommitRepoPair("A", "foo")
        commit_b = CommitRepoPair("B", "foo")
        commit_c = CommitRepoPair("C", "foo")
        commit_d = CommitRepoPair("D", "foo")

        fix_in = {commit_a, commit_b}
        fix_out = {commit_c, commit_d}
        intro_in = {commit_a, commit_b}
        intro_out = {commit_c, commit_d}

        self.assertEqual(
            1,
            _calculate_szz_quality_score(fix_in, fix_out, intro_in, intro_out)
        )

    def test_calculate_szz_quality_score_empty_interactions(self) -> None:
        """Test SZZ quality score calculation."""
        self.assertEqual(
            -1, _calculate_szz_quality_score(set(), set(), set(), set())
        )

    def test_calculate_szz_quality_score_partial_match(self) -> None:
        """Test SZZ quality score calculation."""
        commit_a = CommitRepoPair("A", "foo")
        commit_b = CommitRepoPair("B", "foo")
        commit_c = CommitRepoPair("C", "foo")
        commit_d = CommitRepoPair("D", "foo")
        commit_e = CommitRepoPair("E", "foo")
        commit_f = CommitRepoPair("F", "foo")

        fix_in = {commit_a, commit_b, commit_e}
        fix_out = {commit_c, commit_d}
        intro_in = {commit_a, commit_b, commit_f}
        intro_out = {commit_c, commit_d, commit_e, commit_f}

        self.assertEqual(
            0.5,
            _calculate_szz_quality_score(fix_in, fix_out, intro_in, intro_out)
        )

    def test_calculate_szz_quality_score_weighting(self) -> None:
        """Test SZZ quality score calculation."""
        commit_a = CommitRepoPair("A", "foo")
        commit_b = CommitRepoPair("B", "foo")
        commit_c = CommitRepoPair("C", "foo")
        commit_d = CommitRepoPair("D", "foo")

        fix_in = {commit_a, commit_b}
        fix_out = {commit_c}
        intro_in = {commit_a, commit_b, commit_d}
        intro_out = {commit_c}

        self.assertEqual(
            0.75,
            _calculate_szz_quality_score(fix_in, fix_out, intro_in, intro_out)
        )
