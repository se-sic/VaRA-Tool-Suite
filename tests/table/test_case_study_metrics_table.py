"""Test bug overview table."""
import unittest

from tests.test_utils import run_in_test_environment, UnitTestFixtures
from varats.paper_mgmt.paper_config import load_paper_config
from varats.projects.discover_projects import initialize_projects
from varats.table.tables import TableFormat, TableConfig
from varats.tables.case_study_metrics_table import CaseStudyMetricsTable
from varats.utils.git_util import FullCommitHash
from varats.utils.settings import vara_cfg


class TestCSMetricsTable(unittest.TestCase):
    """Test whether case study metrics are collected correctly."""

    @run_in_test_environment(UnitTestFixtures.PAPER_CONFIGS)
    def test_one_case_study_latex_booktabs(self) -> None:
        """"Tests the latex booktabs format for the cs overview table."""
        vara_cfg()["paper_config"]["current_config"] = "test_revision_lookup"
        initialize_projects()
        load_paper_config()

        # latex booktabs is default format
        table_str = CaseStudyMetricsTable(
            TableConfig.from_kwargs(view=False),
            revisions={
                "brotli":
                    FullCommitHash("ce222e317e36aa362e83fc50c7a6226d238e03fd")
            }
        ).tabulate(TableFormat.LATEX_BOOKTABS)

        self.assertEqual(
            r"""\begin{tabular}{llrrrl}
\toprule
{} &       Domain &    LOC &  Commits &  Authors &    Revision \\
\midrule
\textbf{brotli} &  Compression &  34833 &     1030 &       87 &  ce222e317e \\
\bottomrule
\end{tabular}
""", table_str
        )

    @run_in_test_environment(UnitTestFixtures.PAPER_CONFIGS)
    def test_multiple_case_studies_latex_booktabs(self) -> None:
        """"Tests the latex booktabs format for the cs overview table."""
        vara_cfg()["paper_config"]["current_config"] = "test_artefacts_driver"
        initialize_projects()
        load_paper_config()

        # latex booktabs is default format
        table_str = CaseStudyMetricsTable(
            TableConfig.from_kwargs(view=False),
            revisions={
                "xz":
                    FullCommitHash("c5c7ceb08a011b97d261798033e2c39613a69eb7")
            }
        ).tabulate(TableFormat.LATEX_BOOKTABS)

        self.assertEqual(
            r"""\begin{tabular}{llrrrl}
\toprule
{} &                Domain &    LOC &  Commits &  Authors &    Revision \\
\midrule
\textbf{gravity} &  Programming language &  22923 &      663 &       39 &  2c71dec8ad \\
\textbf{xz     } &           Compression &  37021 &     1143 &       16 &  c5c7ceb08a \\
\bottomrule
\end{tabular}
""", table_str
        )
