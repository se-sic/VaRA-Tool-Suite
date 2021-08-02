"""Test varats container tool."""
import unittest

from click.testing import CliRunner

from tests.test_utils import run_in_test_environment, UnitTestInputs
from varats.tools import driver_run
from varats.utils.settings import vara_cfg


class TestDriverRun(unittest.TestCase):
    """Tests for the driver_container module."""

    @run_in_test_environment(UnitTestInputs.PAPER_CONFIGS)
    def test_bb_run_just_compile_brotli(self) -> None:
        runner = CliRunner()
        vara_cfg()['paper_config']['current_config'] = "test_revision_lookup"
        result = runner.invoke(driver_run.main, ["-E", "JustCompile"])
        print(result.stdout)
        self.assertEqual(0, result.exit_code, result.exception)
