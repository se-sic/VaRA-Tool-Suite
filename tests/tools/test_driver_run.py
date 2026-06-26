"""Test varats container tool."""

import importlib
import re
import unittest
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from tests.helper_utils import (
    ExternalRepoFixture,
    UnitTestFixtures,
    run_in_test_environment,
)
from varats.experiments import discover_experiments
from varats.paper.paper_config import load_paper_config
from varats.projects import discover_projects
from varats.tools import driver_external, driver_run
from varats.utils.settings import bb_cfg, save_config, vara_cfg


class TestDriverRun(unittest.TestCase):
    """Tests for the driver_container module."""

    __NUM_ACTIONS_PATTERN = re.compile(r"Number of actions to execute: (\d*)")

    @run_in_test_environment(UnitTestFixtures.PAPER_CONFIGS)
    def test_bb_run_select_project(self) -> None:
        runner = CliRunner()
        vara_cfg()['paper_config']['current_config'] = "test_artefacts_driver"
        # needed so we see the paper config
        load_paper_config()
        # needed so benchbuild sees the paper config
        save_config()

        result = runner.invoke(
            driver_run.main, ["-vvv", "-p", "-E", "JustCompile", "xz"]
        )
        self.assertEqual(0, result.exit_code, result.exception)
        match = self.__NUM_ACTIONS_PATTERN.search(result.stdout)
        if not match:
            self.fail("Could not parse benchbuild output")
        self.assertEqual("44", match.group(1))

    @run_in_test_environment(UnitTestFixtures.PAPER_CONFIGS)
    def test_bb_run_select_revision(self) -> None:
        runner = CliRunner()
        vara_cfg()['paper_config']['current_config'] = "test_artefacts_driver"
        # needed so we see the paper config
        load_paper_config()
        # needed so benchbuild sees the paper config
        save_config()

        result = runner.invoke(
            driver_run.main, ["-p", "-E", "JustCompile", "xz@2f0bc9cd40"]
        )
        self.assertEqual(0, result.exit_code, result.exception)
        match = self.__NUM_ACTIONS_PATTERN.search(result.stdout)
        if not match:
            self.fail("Could not parse benchbuild output")
        self.assertEqual("12", match.group(1))

    @run_in_test_environment(UnitTestFixtures.PAPER_CONFIGS)
    def test_bb_run_all(self) -> None:
        runner = CliRunner()
        vara_cfg()['paper_config']['current_config'] = "test_artefacts_driver"
        # needed so we see the paper config
        load_paper_config()
        # needed so benchbuild sees the paper config
        save_config()

        result = runner.invoke(driver_run.main, ["-p", "-E", "JustCompile"])
        self.assertEqual(0, result.exit_code, result.exception)
        match = self.__NUM_ACTIONS_PATTERN.search(result.stdout)
        if not match:
            self.fail("Could not parse benchbuild output")
        self.assertEqual("52", match.group(1))

    @run_in_test_environment(UnitTestFixtures.PAPER_CONFIGS)
    @mock.patch("varats.tools.driver_run.sbatch")
    def test_bb_run_slurm_and_container(self, mock_sbatch) -> None:  # noqa: ARG002
        runner = CliRunner()
        vara_cfg()['paper_config']['current_config'] = "test_revision_lookup"
        # needed so we see the paper config
        load_paper_config()
        # needed so benchbuild sees the paper config
        save_config()

        result = runner.invoke(
            driver_run.main, ["--slurm", "--container", "-E", "JustCompile"]
        )
        self.assertEqual(0, result.exit_code, result.exception)
        self.assertTrue(Path(str(bb_cfg()["slurm"]["template"])).exists())
        self.assertTrue(
            (
                Path(str(vara_cfg()["benchbuild_root"]))
                / "JustCompile-slurm.sh"
            ).exists()
        )

    @run_in_test_environment(
        ExternalRepoFixture(), UnitTestFixtures.PAPER_CONFIGS
    )
    def test_bb_run_external_project(self) -> None:
        runner = CliRunner()

        repo_path = Path.cwd() / "external_repo"
        driver_external.register_external_repository(repo_path)
        # Force project discovery to run again so the newly registered
        # external repository's project gets picked up.
        setattr(discover_projects, "__PROJECTS_DISCOVERED", False)

        vara_cfg()['paper_config']['current_config'] = "test_external_project"
        load_paper_config()
        save_config()

        result = runner.invoke(
            driver_run.main,
            ["-vvv", "-p", "-E", "JustCompile", "external_project"],
        )
        self.assertEqual(0, result.exit_code, result.output)
        match = self.__NUM_ACTIONS_PATTERN.search(result.stdout)
        if not match:
            self.fail("Could not parse benchbuild output")
        self.assertEqual("12", match.group(1))

    @run_in_test_environment(
        ExternalRepoFixture(), UnitTestFixtures.PAPER_CONFIGS
    )
    def test_bb_run_select_internal_project_after_registering_external(
        self,
    ) -> None:
        runner = CliRunner()

        repo_path = Path.cwd() / "external_repo"
        driver_external.register_external_repository(repo_path)
        # Force project discovery to run again so the newly registered
        # external repository's project gets picked up.
        setattr(discover_projects, "__PROJECTS_DISCOVERED", False)

        vara_cfg()['paper_config']['current_config'] = "test_artefacts_driver"
        load_paper_config()
        save_config()

        result = runner.invoke(
            driver_run.main, ["-p", "-E", "JustCompile", "gravity"]
        )
        self.assertEqual(0, result.exit_code, result.output)
        match = self.__NUM_ACTIONS_PATTERN.search(result.stdout)
        if not match:
            self.fail("Could not parse benchbuild output")
        self.assertEqual("12", match.group(1))

    @run_in_test_environment(
        ExternalRepoFixture(), UnitTestFixtures.PAPER_CONFIGS
    )
    def test_bb_run_external_experiment(self) -> None:
        """`vara-run` can select and plan actions for an experiment that is
        registered from an external repository."""
        runner = CliRunner()

        repo_path = Path.cwd() / "external_repo"
        driver_external.register_external_repository(repo_path)
        # Force experiment discovery to run again so the newly registered
        # external repository's experiment gets picked up.
        setattr(discover_experiments, "__EXPERIMENTS_DISCOVERED", False)

        # The `-E` choice list is built once, when `driver_run` is imported,
        # so newly registered experiments are invisible to it unless we
        # reimport the module to rebuild it.
        reloaded_driver_run = importlib.reload(driver_run)

        vara_cfg()['paper_config']['current_config'] = "test_artefacts_driver"
        # needed so we see the paper config
        load_paper_config()
        # needed so benchbuild sees the paper config
        save_config()

        result = runner.invoke(
            reloaded_driver_run.main, ["-p", "-E", "ExternalExperiment", "xz"]
        )
        self.assertEqual(0, result.exit_code, result.output)
        match = self.__NUM_ACTIONS_PATTERN.search(result.stdout)
        if not match:
            self.fail("Could not parse benchbuild output")
        self.assertEqual("29", match.group(1))
