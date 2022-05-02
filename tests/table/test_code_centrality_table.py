"""Test bug overview table."""
import unittest

from tests.test_utils import run_in_test_environment, UnitTestFixtures
from varats.paper_mgmt.paper_config import (
    load_paper_config,
    get_loaded_paper_config,
)
from varats.projects.discover_projects import initialize_projects
from varats.table.tables import TableConfig, TableFormat
from varats.tables.code_centrality_table import TopCentralCodeCommitsTable
from varats.utils.settings import vara_cfg


class TestCSMetricsTable(unittest.TestCase):
    """Test whether case study metrics are collected correctly."""

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_one_case_study_latex_booktabs(self) -> None:
        """Tests the latex booktabs format for the code centrality metrics
        table."""
        vara_cfg()["paper_config"]["current_config"
                                  ] = "test_diff_correlation_overview_table"
        initialize_projects()
        load_paper_config()

        # latex booktabs is default format
        table_str = TopCentralCodeCommitsTable(
            TableConfig.from_kwargs(view=False),
            case_study=get_loaded_paper_config().get_case_studies("xz")[0],
            num_commits=10
        ).tabulate(TableFormat.LATEX_BOOKTABS, False)

        self.assertEqual(
            r"""\begin{table}
\centering
\caption{Top 10 Central Code Commits}
\begin{tabular}{lr}
\toprule
                                  commit &  centrality \\
\midrule
ef68dd4a92976276304de2aedfbe34ae91a86abb &          28 \\
57597d42ca1740ad506437be168d800a50f1a0ad &          16 \\
ea00545beace5b950f709ec21e46878e0f448678 &          16 \\
7f0a4c50f4a374c40acf4b86848f301ad1e82d34 &          15 \\
c15c42abb3c8c6e77c778ef06c97a4a10b8b5d00 &          15 \\
fa3ab0df8ae7a8a1ad55b52266dc0fd387458671 &          10 \\
1d924e584b146136989f48c13fff2632896efb3d &           9 \\
d8b41eedce486d400f701b757b7b5e4e32276618 &           8 \\
1b0ac0c53c761263e91e34195cb21dfdcfeac0bd &           6 \\
e0ea6737b03e83ccaff4514d00e31bb926f8f0f3 &           6 \\
\bottomrule
\end{tabular}
\end{table}
""", table_str
        )
