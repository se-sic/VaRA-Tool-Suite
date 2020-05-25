import unittest

import pytest

from tests.test_utils import replace_config, TEST_INPUTS_DIR
from varats.tables import diff_correlation_overview_table


class TestDiffCorrelationOverviewTable(unittest.TestCase):

    @pytest.mark.slow
    @replace_config()
    def test_table_tex_output2(self, config):
        config["paper_config"]["current_config"
                              ] = "test_diff_correlation_overview_table"
        table = diff_correlation_overview_table.DiffCorrelationOverviewTable(
        ).tabulate()

        with open(
            TEST_INPUTS_DIR / "tables" / "b_diff_correlation_overview.tex"
        ) as expected:
            assert table == expected.read()
