"""Test blame interaction graphs."""

import unittest

import pytest

from tests.test_utils import run_in_test_environment, UnitTestInputs
from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
    create_file_based_interaction_graph,
    get_author_data,
)
from varats.data.reports.blame_report import BlameReport
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.paper_mgmt.paper_config import load_paper_config, get_paper_config
from varats.projects.discover_projects import initialize_projects
from varats.utils.settings import vara_cfg


class TestBlameInteractionGraphs(unittest.TestCase):
    """Test if blame interaction graphs are constructed correctly."""

    @classmethod
    def setUpClass(cls):
        initialize_projects()

    @run_in_test_environment(
        UnitTestInputs.PAPER_CONFIGS, UnitTestInputs.RESULT_FILES
    )
    def test_blame_interaction_graph(self) -> None:
        """Test whether blame interaction graphs are created correctly."""
        vara_cfg()['paper_config']['current_config'] = "test_casestudy_status"
        load_paper_config()

        revision = newest_processed_revision_for_case_study(
            get_paper_config().get_case_studies("xz")[0], BlameReport
        )
        blame_interaction_graph = create_blame_interaction_graph("xz", revision)

        self.assertEqual(blame_interaction_graph.project_name, "xz")

        cig = blame_interaction_graph.commit_interaction_graph()
        self.assertEqual(74, len(cig.nodes))
        self.assertEqual(475, len(cig.edges))

        aig = blame_interaction_graph.author_interaction_graph()
        self.assertEqual(2, len(aig.nodes))
        self.assertEqual(2, len(aig.edges))

        caig = blame_interaction_graph.commit_author_interaction_graph()
        self.assertEqual(76, len(caig.nodes))
        self.assertEqual(57, len(caig.edges))

    @pytest.mark.slow
    @run_in_test_environment(
        UnitTestInputs.PAPER_CONFIGS, UnitTestInputs.RESULT_FILES
    )
    def test_file_based_interaction_graph(self) -> None:
        """Test whether file-based interaction graphs are created correctly."""
        vara_cfg()['paper_config']['current_config'] = "test_casestudy_status"
        load_paper_config()

        revision = newest_processed_revision_for_case_study(
            get_paper_config().get_case_studies("xz")[0], BlameReport
        )
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
        UnitTestInputs.PAPER_CONFIGS, UnitTestInputs.RESULT_FILES
    )
    def test_get_author_data(self) -> None:
        """Check whether author data is retrieved correctly from the author
        interaction graph."""
        vara_cfg()['paper_config']['current_config'] = "test_casestudy_status"
        load_paper_config()

        revision = newest_processed_revision_for_case_study(
            get_paper_config().get_case_studies("xz")[0], BlameReport
        )
        blame_interaction_graph = create_blame_interaction_graph("xz", revision)

        self.assertEqual(blame_interaction_graph.project_name, "xz")

        aig = blame_interaction_graph.author_interaction_graph()
        author_data = get_author_data(aig, "Lasse Collin")
        self.assertEqual(author_data["node_attrs"]["author"], "Lasse Collin")
        self.assertEqual(author_data["neighbors"], {"Jonathan Nieder"})
        self.assertEqual(2, len(author_data["in_attrs"][0]))
        self.assertEqual(3, len(author_data["out_attrs"][0]))
