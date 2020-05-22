import unittest

from tests.test_utils import replace_config, TEST_INPUTS_DIR
from varats.data.reports.commit_report import CommitMap
from varats.tables import diff_correlation_overview_table
from varats.tools.commit_map import get_commit_map


def mocked_get_commit_map(project_name: str) -> CommitMap:
    return {
        "gzip": get_commit_map("xz", TEST_INPUTS_DIR / "cmaps" / "gzip.cmap"),
        "xz": get_commit_map("xz", TEST_INPUTS_DIR / "cmaps" / "xz.cmap"),
    }[project_name]


class TestDiffCorrelationOverviewTable(unittest.TestCase):

    @replace_config()
    def test_table_tex_output(self, config):
        config["paper_config"]["current_config"
                              ] = "test_diff_correlation_overview_table"
        # monkey-patch the table's get_commit_map()
        get_commit_map_orig = diff_correlation_overview_table.get_commit_map
        diff_correlation_overview_table.get_commit_map = mocked_get_commit_map

        table = diff_correlation_overview_table.DiffCorrelationOverviewTable(
        ).tabulate()

        with open(
            TEST_INPUTS_DIR / "tables" / "b_diff_correlation_overview.tex"
        ) as expected:
            self.assertEqual(table, expected.read())

        # restore monkey patch
        diff_correlation_overview_table.get_commit_map = get_commit_map_orig

    def test_table_tex_output2(self):
        with replace_config() as config:
            config["paper_config"]["current_config"
                                  ] = "test_diff_correlation_overview_table"
            # monkey-patch the table's get_commit_map()
            get_commit_map_orig = diff_correlation_overview_table.get_commit_map
            diff_correlation_overview_table.get_commit_map = mocked_get_commit_map

            table = diff_correlation_overview_table.DiffCorrelationOverviewTable(
            ).tabulate()

            with open(
                TEST_INPUTS_DIR / "tables" / "b_diff_correlation_overview.tex"
            ) as expected:
                self.assertEqual(table, expected.read())

            # restore monkey patch
            diff_correlation_overview_table.get_commit_map = get_commit_map_orig
