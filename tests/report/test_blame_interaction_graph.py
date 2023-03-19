"""Test blame interaction graphs."""

import unittest

import pytest

from tests.helper_utils import run_in_test_environment, UnitTestFixtures
from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
    create_file_based_interaction_graph,
    get_author_data,
)
from varats.data.reports.blame_report import BlameReport
from varats.experiments.vara.blame_report_experiment import (
    BlameReportExperiment,
)
from varats.paper.paper_config import load_paper_config, get_paper_config
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.projects.discover_projects import initialize_projects
from varats.utils.settings import vara_cfg


class TestBlameInteractionGraphs(unittest.TestCase):
    """Test if blame interaction graphs are constructed correctly."""

    @classmethod
    def setUpClass(cls):
        initialize_projects()

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_blame_interaction_graph(self) -> None:
        """Test whether blame interaction graphs are created correctly."""
        vara_cfg()['paper_config']['current_config'] = "test_casestudy_status"
        load_paper_config()

        revision = newest_processed_revision_for_case_study(
            get_paper_config().get_case_studies("xz")[0], BlameReportExperiment
        )
        assert revision
        blame_interaction_graph = create_blame_interaction_graph(
            "xz", revision, BlameReportExperiment
        )

        self.assertEqual(blame_interaction_graph.project_name, "xz")

        cig = blame_interaction_graph.commit_interaction_graph()
        self.assertEqual(124, len(cig.nodes))
        self.assertEqual(928, len(cig.edges))

        aig = blame_interaction_graph.author_interaction_graph()
        self.assertEqual(1, len(aig.nodes))
        self.assertEqual(0, len(aig.edges))

        caig = blame_interaction_graph.commit_author_interaction_graph()
        self.assertEqual(125, len(caig.nodes))
        self.assertEqual(92, len(caig.edges))

    @pytest.mark.slow
    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_file_based_interaction_graph(self) -> None:
        """Test whether file-based interaction graphs are created correctly."""
        vara_cfg()['paper_config']['current_config'] = "test_casestudy_status"
        load_paper_config()

        revision = newest_processed_revision_for_case_study(
            get_paper_config().get_case_studies("xz")[0], BlameReportExperiment
        )
        assert revision
        blame_interaction_graph = create_file_based_interaction_graph(
            "xz", revision
        )

        self.assertEqual(blame_interaction_graph.project_name, "xz")

        cig = blame_interaction_graph.commit_interaction_graph()
        self.assertEqual(482, len(cig.nodes))
        self.assertEqual(16518, len(cig.edges))

        aig = blame_interaction_graph.author_interaction_graph()
        self.assertEqual(4, len(aig.nodes))
        self.assertEqual(6, len(aig.edges))

        caig = blame_interaction_graph.commit_author_interaction_graph()
        self.assertEqual(486, len(caig.nodes))
        self.assertEqual(509, len(caig.edges))

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_get_author_data(self) -> None:
        """Check whether author data is retrieved correctly from the author
        interaction graph."""
        vara_cfg()['paper_config']['current_config'] = "test_casestudy_status"
        load_paper_config()

        revision = newest_processed_revision_for_case_study(
            get_paper_config().get_case_studies("xz")[0], BlameReportExperiment
        )
        assert revision
        blame_interaction_graph = create_blame_interaction_graph(
            "xz", revision, BlameReportExperiment
        )

        self.assertEqual(blame_interaction_graph.project_name, "xz")

        aig = blame_interaction_graph.author_interaction_graph()
        author_data = get_author_data(aig, "Lasse Collin")
        self.assertEqual(author_data["node_attrs"]["author"], "Lasse Collin")
        self.assertEqual(author_data["neighbors"], set())
        self.assertEqual(0, len(author_data["in_attrs"]))
        self.assertEqual(0, len(author_data["out_attrs"]))
