"""Test bug overview table."""
import unittest

from tests.test_utils import run_in_test_environment, UnitTestFixtures
from varats.paper_mgmt.paper_config import (
    load_paper_config,
    get_loaded_paper_config,
)
from varats.projects.discover_projects import initialize_projects
from varats.table.tables import TableConfig, TableFormat
from varats.tables.blame_interaction_graph_table import (
    CommitInteractionGraphMetricsTable,
    AuthorInteractionGraphMetricsTable,
    CommitAuthorInteractionGraphMetricsTable,
    AuthorBlameVsFileDegreesTable,
)
from varats.utils.settings import vara_cfg


class TestCSMetricsTable(unittest.TestCase):
    """Test whether case study metrics are collected correctly."""

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_cig_metrics_table(self) -> None:
        """Tests the latex booktabs format for the cig metrics table."""
        vara_cfg()["paper_config"]["current_config"
                                  ] = "test_diff_correlation_overview_table"
        initialize_projects()
        load_paper_config()

        # latex booktabs is default format
        table_str = CommitInteractionGraphMetricsTable(
            TableConfig.from_kwargs(view=False),
            case_study=get_loaded_paper_config().get_all_case_studies()
        ).tabulate(TableFormat.LATEX_BOOKTABS, False)

        self.assertEqual(
            r"""\begin{tabular}{lrrrrrrrrrrrrrr}
\toprule
{} & commits & authors & nodes & edges & \multicolumn{4}{c}{node degree} & \multicolumn{3}{c}{node out degree} & \multicolumn{3}{c}{node in degree} \\
{} &        mean & median & min &  max &          median & min & max &         median & min & max \\
\midrule
\textbf{xz} &    1143 &      28 &   124 &   928 &       14.97 &    8.0 &   1 &  154 &             4.0 &   0 &  64 &            3.0 &   0 &  92 \\
\bottomrule
\end{tabular}
""", table_str
        )

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_aig_metrics_table(self) -> None:
        """Tests the latex booktabs format for the aig metrics table."""
        vara_cfg()["paper_config"]["current_config"
                                  ] = "test_diff_correlation_overview_table"
        initialize_projects()
        load_paper_config()

        # latex booktabs is default format
        table_str = AuthorInteractionGraphMetricsTable(
            TableConfig.from_kwargs(view=False),
            case_study=get_loaded_paper_config().get_all_case_studies()
        ).tabulate(TableFormat.LATEX_BOOKTABS, False)

        self.assertEqual(
            r"""\begin{tabular}{lrrrrrrrrrrrrrr}
\toprule
{} & commits & authors & nodes & edges & \multicolumn{4}{c}{node degree} & \multicolumn{3}{c}{node out degree} & \multicolumn{3}{c}{node in degree} \\
{} &        mean & median & min & max &          median & min & max &         median & min & max \\
\midrule
\textbf{xz} &    1143 &      28 &     1 &     0 &         0.0 &    0.0 &   0 &   0 &             0.0 &   0 &   0 &            0.0 &   0 &   0 \\
\bottomrule
\end{tabular}
""", table_str
        )

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_caig_metrics_table(self) -> None:
        """Tests the latex booktabs format for the caig metrics table."""
        vara_cfg()["paper_config"]["current_config"
                                  ] = "test_diff_correlation_overview_table"
        initialize_projects()
        load_paper_config()

        # latex booktabs is default format
        table_str = CommitAuthorInteractionGraphMetricsTable(
            TableConfig.from_kwargs(view=False),
            case_study=get_loaded_paper_config().get_all_case_studies()
        ).tabulate(TableFormat.LATEX_BOOKTABS, False)

        self.assertEqual(
            r"""\begin{tabular}{lrrrrrrrrrrrrrr}
\toprule
{} & commits & authors & nodes & edges & \multicolumn{4}{c}{node degree} & \multicolumn{3}{c}{node out degree} & \multicolumn{3}{c}{node in degree} \\
{} &        mean & median & min & max &          median & min & max &         median & min & max \\
\midrule
\textbf{xz} &    1143 &      28 &   125 &    92 &        1.47 &    1.0 &   0 &  92 &             1.0 &   0 &   1 &            0.0 &   0 &  92 \\
\bottomrule
\end{tabular}
""", table_str
        )

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_aig_file_vs_blame_degrees_table(self) -> None:
        """
        Tests the latex booktabs format for the file vs.

        ci table.
        """
        vara_cfg()["paper_config"]["current_config"
                                  ] = "test_diff_correlation_overview_table"
        initialize_projects()
        load_paper_config()

        # latex booktabs is default format
        table_str = AuthorBlameVsFileDegreesTable(
            TableConfig.from_kwargs(view=False),
            case_study=get_loaded_paper_config().get_case_studies("xz")[0]
        ).tabulate(TableFormat.LATEX_BOOKTABS, False)

        self.assertEqual(
            r"""\begin{tabular}{lrrrrr}
\toprule
{} &  blame\_num\_commits &  blame\_node\_degree &  author\_diff &  file\_num\_commits &  file\_node\_degree \\
author         &                    &                    &              &                   &                   \\
\midrule
Alexey Tourbin &                NaN &                NaN &          NaN &                 1 &                 2 \\
Ben Boeckel    &                NaN &                NaN &          NaN &                 1 &                 2 \\
Jim Meyering   &                NaN &                NaN &          NaN &                 1 &                 2 \\
Lasse Collin   &              124.0 &                0.0 &          0.0 &               479 &                 6 \\
\bottomrule
\end{tabular}
""", table_str
        )
