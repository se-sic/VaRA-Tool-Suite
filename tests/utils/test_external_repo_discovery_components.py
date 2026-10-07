"""Integration test for External Repository component discovery."""

import sys
import unittest
from pathlib import Path

from benchbuild.experiment import ExperimentRegistry
from click.testing import CliRunner

import varats.experiments as varats_experiments
import varats.tables as varats_tables
from tests.helper_utils import ExternalRepoFixture, run_in_test_environment
from varats.data.reports import discover as discover_reports
from varats.plots import discover as discover_plots
from varats.projects import discover as discover_projects
from varats.table.tables import TableGenerator
from varats.tools import driver_external
from varats.tools.tool_util import (
    get_research_tool_type,
    get_supported_research_tool_names,
)


class TestExternalRepoDiscoveryComponents(unittest.TestCase):
    """Tests discovery of all External Repository component types."""

    EXTERNAL_REPO_TEMPLATE = ExternalRepoFixture()

    @run_in_test_environment(EXTERNAL_REPO_TEMPLATE)
    def test_external_repo_discovery_includes_all_components(self) -> None:
        repo_path = Path.cwd() / "external_repo"

        runner = CliRunner()
        result = runner.invoke(driver_external.main, ["set", str(repo_path)])
        self.assertEqual(0, result.exit_code)

        # Discover all components
        varats_experiments.discover()
        varats_tables.discover()

        discover_plots()
        discover_projects()
        discover_reports()

        # Verify experiments are discovered
        self.assertTrue(
            any(
                experiment_type.__name__ == "ExternalExperiment"
                for experiment_type in ExperimentRegistry.experiments.values()
            )
        )

        # Verify tables are discovered
        self.assertTrue(
            any(
                table_type.__name__ == "ExternalTableGenerator"
                for table_type in TableGenerator.GENERATORS.values()
            )
        )

        # Verify research tools are discovered
        self.assertIn(
            "externalresearchtool", get_supported_research_tool_names()
        )
        self.assertIsNotNone(get_research_tool_type("externalresearchtool"))

        # Verify that plots module can be imported (external plots loaded)
        self.assertTrue(
            any(
                "external_plot" in module_name
                for module_name in sys.modules
                if "plots" in module_name
            )
        )

        # Verify that projects module can be imported (external projects loaded)
        self.assertTrue(
            any(
                "external_project" in module_name
                for module_name in sys.modules
                if "projects" in module_name
            )
        )

        # Verify that reports module can be imported (external reports loaded)
        self.assertTrue(
            any(
                "external_report" in module_name
                for module_name in sys.modules
                if "reports" in module_name
            )
        )
