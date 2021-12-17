"""Test varats container tool."""
import unittest
from pathlib import Path

from click.testing import CliRunner

from tests.test_utils import run_in_test_environment
from varats.tools import driver_build_setup
from varats.utils.settings import vara_cfg


class TestDriverBuildsetup(unittest.TestCase):
    """Tests for the driver_build_setup module."""

    @run_in_test_environment()
    def test_init_config(self) -> None:
        config_path = Path(vara_cfg()["config_file"].value)
        config_path.unlink(missing_ok=True)
        self.assertFalse(config_path.exists())
        runner = CliRunner()
        result = runner.invoke(driver_build_setup.main, ["config"])
        self.assertEqual(0, result.exit_code, result.exception)
        self.assertTrue(config_path.exists())
