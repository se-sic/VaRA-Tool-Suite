"""Test the DiffCorrelationOverviewTable class."""
import unittest

import pytest

from tests.test_utils import replace_config, TEST_INPUTS_DIR
from varats.paper.paper_config import load_paper_config
from varats.tables import diff_correlation_overview_table


class TestDiffCorrelationOverviewTable(unittest.TestCase):
    """Test the DiffCorrelationOverviewTable class."""

    @pytest.mark.slow
    @replace_config()
    def test_table_tex_output(self, config):
        """Check whether the table produces the correct tex output."""
        config["paper_config"]["current_config"
                              ] = "test_diff_correlation_overview_table"
        load_paper_config()
        table = diff_correlation_overview_table.DiffCorrelationOverviewTable(
        ).tabulate()

        with open(
            TEST_INPUTS_DIR / "tables" / "b_diff_correlation_overview.tex"
        ) as expected:
            self.assertEqual(table, expected.read())
