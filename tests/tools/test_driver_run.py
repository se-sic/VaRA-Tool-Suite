"""Test varats container tool."""
import re
import unittest
import unittest.mock as mock
from pathlib import Path

from click.testing import CliRunner

from tests.test_utils import run_in_test_environment, UnitTestInputs
from varats.paper_mgmt.paper_config import load_paper_config
from varats.tools import driver_run, driver_container
from varats.utils.settings import vara_cfg, save_config, bb_cfg, save_bb_config


class TestDriverRun(unittest.TestCase):
    """Tests for the driver_container module."""

    __NUM_ACTIONS_PATTERN = re.compile(r"Number of actions to execute: (\d*)")

    @run_in_test_environment(UnitTestInputs.PAPER_CONFIGS)
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
        self.assertEqual("43", match.group(1))

    @run_in_test_environment(UnitTestInputs.PAPER_CONFIGS)
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
        self.assertEqual("11", match.group(1))

    @run_in_test_environment(UnitTestInputs.PAPER_CONFIGS)
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
        self.assertEqual("51", match.group(1))

    @run_in_test_environment(UnitTestInputs.PAPER_CONFIGS)
    @mock.patch("varats.tools.driver_run.sbatch")
    @mock.patch("varats.tools.driver_container.__build_images")
    def test_bb_run_slurm_and_container(
        self, mock_sbatch, mock_build_images
    ) -> None:
        runner = CliRunner()
        vara_cfg()['paper_config']['current_config'] = "test_revision_lookup"
        # needed so we see the paper config
        load_paper_config()
        # needed so benchbuild sees the paper config
        save_config()

        bb_cfg()["slurm"]["template"] = str(
            Path(str(vara_cfg()["benchbuild_root"])) / "slurm_container.sh.inc"
        )
        save_bb_config()

        # Easiest way to configure slurm + container is 'vara-container'
        # As a side-effect, this command is now even more tested :)
        prepare_result = runner.invoke(driver_container.main, ["prepare-slurm"])
        self.assertEqual(0, prepare_result.exit_code, prepare_result.exception)
        self.assertTrue(Path(str(bb_cfg()["slurm"]["template"])).exists())

        result = runner.invoke(
            driver_run.main, ["--slurm", "--container", "-E", "JustCompile"]
        )
        self.assertEqual(0, result.exit_code, result.exception)
        self.assertTrue(
            (Path(str(vara_cfg()["benchbuild_root"])) /
             "JustCompile-slurm.sh").exists()
        )
