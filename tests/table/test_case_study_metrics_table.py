"""Test bug overview table."""
import unittest

from tests.test_utils import run_in_test_environment, UnitTestInputs
from varats.paper_mgmt.paper_config import load_paper_config
from varats.projects.discover_projects import initialize_projects
from varats.tables.case_study_metrics_table import CaseStudyMetricsTable
from varats.utils.git_util import FullCommitHash
from varats.utils.settings import vara_cfg


class TestCSMetricsTable(unittest.TestCase):
    """Test whether case study metrics are collected correctly."""

    @run_in_test_environment(UnitTestInputs.PAPER_CONFIGS)
    def test_one_case_study_latex_booktabs(self) -> None:
        """"Tests the latex booktabs format for the cs overview table."""
        vara_cfg()["paper_config"]["current_config"] = "test_revision_lookup"
        initialize_projects()
        load_paper_config()

        # latex booktabs is default format
        table_str = CaseStudyMetricsTable(
            revisions={
                "brotli":
                    FullCommitHash("ce222e317e36aa362e83fc50c7a6226d238e03fd")
            }
        ).tabulate()

        self.assertEqual(
            r"""\begin{tabular}{llrrrl}
\toprule
{} &       Domain &    LOC &  Commits &  Authors & Analyzed Commit \\
\midrule
\textbf{brotli} &  compression &  37033 &     1030 &       87 &      ce222e317e \\
\bottomrule
\end{tabular}
""", table_str
        )

    @run_in_test_environment(UnitTestInputs.PAPER_CONFIGS)
    def test_multiple_case_studies_latex_booktabs(self) -> None:
        """"Tests the latex booktabs format for the cs overview table."""
        vara_cfg()["paper_config"]["current_config"] = "test_artefacts_driver"
        initialize_projects()
        load_paper_config()

        # latex booktabs is default format
        table_str = CaseStudyMetricsTable(
            revisions={
                "xz":
                    FullCommitHash("c5c7ceb08a011b97d261798033e2c39613a69eb7")
            }
        ).tabulate()

        self.assertEqual(
            r"""\begin{tabular}{llrrrl}
\toprule
{} &       Domain &    LOC &  Commits &  Authors & Analyzed Commit \\
\midrule
\textbf{gravity} &   UNIX utils &  28159 &      663 &       50 &      2c71dec8ad \\
\textbf{xz     } &  compression &  46283 &     1143 &       22 &      c5c7ceb08a \\
\bottomrule
\end{tabular}
""", table_str
        )
