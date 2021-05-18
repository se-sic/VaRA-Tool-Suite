"""Test the DiffCorrelationOverviewTable class."""
import unittest

import pytest

from tests.test_utils import TEST_INPUTS_DIR, run_in_test_environment
from varats.paper_mgmt.paper_config import load_paper_config
from varats.tables import diff_correlation_overview_table
from varats.utils.settings import vara_cfg


class TestDiffCorrelationOverviewTable(unittest.TestCase):
    """Test the DiffCorrelationOverviewTable class."""

    @pytest.mark.slow
    @run_in_test_environment
    def test_table_tex_output(self):
        """Check whether the table produces the correct tex output."""
        vara_cfg()["paper_config"]["current_config"
                                  ] = "test_diff_correlation_overview_table"
        load_paper_config()
        table = diff_correlation_overview_table.DiffCorrelationOverviewTable(
        ).tabulate()

        with open(
            TEST_INPUTS_DIR / "tables" / "b_diff_correlation_overview.tex"
        ) as expected:
            self.assertEqual(table, expected.read())
