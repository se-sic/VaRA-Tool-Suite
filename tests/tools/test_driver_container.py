"""Test varats container tool."""
import unittest

from click.testing import CliRunner

from tests.helper_utils import run_in_test_environment
from varats.tools import driver_container
from varats.utils.settings import vara_cfg


class TestDriverContainer(unittest.TestCase):
    """Tests for the driver_container module."""

    @run_in_test_environment()
    def test_container_select(self) -> None:
        runner = CliRunner()
        vara_cfg()["container"]["research_tool"] = None
        result = runner.invoke(driver_container.main, ["select", "-t", "vara"])
        self.assertEqual(0, result.exit_code, result.exception)
        self.assertEqual("vara", str(vara_cfg()["container"]["research_tool"]))
