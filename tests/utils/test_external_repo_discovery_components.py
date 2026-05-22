"""Integration test for External Repository component discovery."""

import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from benchbuild.experiment import ExperimentRegistry
from click.testing import CliRunner

import varats.experiments as varats_experiments
import varats.tables as varats_tables
from tests.helper_utils import run_in_test_environment
from tests.tools.test_driver_external import create_mock_external_repo
from varats.table.tables import TableGenerator
from varats.tools import driver_external
from varats.tools.research_tools.research_tool import ResearchTool
from varats.tools.tool_util import (
    get_research_tool_type,
    get_supported_research_tool_names,
)


class TestExternalRepoDiscoveryComponents(unittest.TestCase):
    """Tests discovery of all External Repository component types."""

    @run_in_test_environment()
    def test_external_repo_discovery_includes_all_components(self) -> None:
        """External experiments, tables, research tools, plots, projects, and reports are discovered."""
        tmp_path = Path(tempfile.mkdtemp())
        repo_path = create_mock_external_repo(tmp_path)
        _create_external_tool_modules(repo_path)

        runner = CliRunner()
        try:
            result = runner.invoke(
                driver_external.main, ["set", str(repo_path)]
            )
            self.assertEqual(0, result.exit_code)

            # Discover all components
            varats_experiments.discover()
            varats_tables.discover()

            # Import discovery functions for plots, projects, and reports
            from varats.data.reports import discover as discover_reports
            from varats.plots import discover as discover_plots
            from varats.projects import discover as discover_projects

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
                    for module_name in sys.modules.keys()
                    if "plots" in module_name
                )
            )

            # Verify that projects module can be imported (external projects loaded)
            self.assertTrue(
                any(
                    "external_project" in module_name
                    for module_name in sys.modules.keys()
                    if "projects" in module_name
                )
            )

            # Verify that reports module can be imported (external reports loaded)
            self.assertTrue(
                any(
                    "external_report" in module_name
                    for module_name in sys.modules.keys()
                    if "reports" in module_name
                )
            )
        finally:
            _cleanup_external_tool_modules(repo_path)


def _create_external_tool_modules(root: Path) -> None:
    """Create dummy external modules for all discoverable components."""
    for folder in [
        "experiments",
        "tables",
        "research_tools",
        "plots",
        "projects",
        "reports",
    ]:
        (root / folder / "__init__.py").write_text("", encoding="utf-8")

    (root / "experiments" / "external_experiment.py").write_text(
        textwrap.dedent(
            '''
            """Dummy external experiment for registry tests."""

            from benchbuild import Project

            from varats.data.reports.empty_report import EmptyReport
            from varats.experiment.experiment_util import VersionExperiment
            from varats.report.report import ReportSpecification


            class ExternalExperiment(VersionExperiment, shorthand="EXT"):
                """Dummy external experiment."""

                NAME = "ExternalExperiment"
                REPORT_SPEC = ReportSpecification(EmptyReport)

                def actions_for_project(self, project: Project):
                    return []
            '''
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (root / "tables" / "external_table.py").write_text(
        textwrap.dedent(
            '''
            """Dummy external table generator for registry tests."""

            from varats.table.tables import TableGenerator


            class ExternalTableGenerator(
                TableGenerator,
                generator_name="external_table",
                options=[]
            ):
                """Dummy external table generator."""

                def generate(self):
                    return []
            '''
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (root / "research_tools" / "external_research_tool.py").write_text(
        textwrap.dedent(
            '''
            """Dummy external research tool for registry tests."""

            from pathlib import Path

            from varats.tools.research_tools.research_tool import (
                Dependencies,
                ResearchTool,
            )
            from varats.tools.research_tools.vara_manager import BuildType


            class ExternalResearchTool(ResearchTool[object]):
                """Dummy external research tool."""

                @classmethod
                def get_dependencies(cls) -> Dependencies:
                    return Dependencies({})

                @staticmethod
                def source_location() -> Path:
                    return Path(".")

                @staticmethod
                def has_source_location() -> bool:
                    return True

                @staticmethod
                def install_location() -> Path:
                    return Path(".")

                @staticmethod
                def has_install_location() -> bool:
                    return True

                def setup(
                    self, source_folder: Path | None, install_prefix: Path,
                    version: int | None
                ) -> None:
                    return None

                def find_highest_sub_prj_version(self, sub_prj_name: str) -> int:
                    return 0

                def is_up_to_date(self) -> bool:
                    return True

                def upgrade(self) -> None:
                    return None

                def build(
                    self, build_type: BuildType, install_location: Path,
                    build_folder_suffix: str | None
                ) -> None:
                    return None

                def get_install_binaries(self) -> list[str]:
                    return []

                def verify_build(
                    self, build_type: BuildType,
                    build_folder_suffix: str | None
                ) -> bool:
                    return True
            '''
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (root / "plots" / "external_plot.py").write_text(
        textwrap.dedent(
            '''
            """Dummy external plot for registry tests."""


            class ExternalPlot:
                """Dummy external plot for registry tests only."""
                pass
            '''
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (root / "projects" / "external_project.py").write_text(
        textwrap.dedent(
            '''
            """Dummy external project for registry tests."""


            class ExternalProject:
                """Dummy external project for registry tests only."""
                pass
            '''
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (root / "reports" / "external_report.py").write_text(
        textwrap.dedent(
            '''
            """Dummy external report for registry tests."""


            class ExternalReport:
                """Dummy external report for registry tests only."""
                pass
            '''
        ).strip()
        + "\n",
        encoding="utf-8",
    )


def _cleanup_external_tool_modules(repo_path: Path) -> None:
    """Remove imported external test modules and registry entries."""
    registry_items = [
        (ExperimentRegistry.experiments, "ExternalExperiment"),
        (TableGenerator.GENERATORS, "external_table"),
        (ResearchTool.REGISTRY, "externalresearchtool"),
    ]

    for registry, expected_name in registry_items:
        for key, value in list(registry.items()):
            if (
                key == expected_name
                or getattr(value, "__name__", "") == expected_name
            ):
                registry.pop(key, None)

    module_names = [
        "experiments.external_experiment",
        "experiments",
        "tables.external_table",
        "tables",
        "research_tools.external_research_tool",
        "research_tools",
        "plots.external_plot",
        "plots",
        "projects.external_project",
        "projects",
        "reports.external_report",
        "reports",
    ]

    for module_name in module_names:
        sys.modules.pop(module_name, None)

    if str(repo_path) in sys.path:
        sys.path.remove(str(repo_path))
