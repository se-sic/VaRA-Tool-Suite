"""Test bug overview table."""
import unittest

from tests.test_utils import run_in_test_environment, UnitTestInputs
from varats.paper_mgmt.paper_config import load_paper_config
from varats.projects.discover_projects import initialize_projects
from varats.tables.case_study_metrics_table import CaseStudyMetricsTable
from varats.utils.settings import vara_cfg


class TestCSMetricsTable(unittest.TestCase):
    """Test whether case study metrics are collected correctly."""

    @run_in_test_environment(UnitTestInputs.PAPER_CONFIGS)
    def test_basic_repo_latex_booktabs(self) -> None:
        """"Tests the latex booktabs format for the cs overview table."""
        vara_cfg()["paper_config"]["current_config"] = "test_revision_lookup"
        initialize_projects()
        load_paper_config()

        # latex booktabs is default format
        table_str = CaseStudyMetricsTable(
            revision="ce222e317e36aa362e83fc50c7a6226d238e03fd"
        ).tabulate()

        self.assertEqual(
            r"""\begin{tabular}{llrrr}
\toprule
{} &       Domain &    LOC &  Commits &  Authors \\
\midrule
\textbf{brotli} &  compression &  37033 &     1030 &       87 \\
\bottomrule
\end{tabular}
""", table_str
        )
