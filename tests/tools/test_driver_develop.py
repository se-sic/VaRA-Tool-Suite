"""Test development tool."""
import unittest

from click.testing import CliRunner

from tests.test_utils import run_in_test_environment
from varats.tools import driver_develop


class TestDriverDevelop(unittest.TestCase):
    """Tests for the driver_develop module."""

    @run_in_test_environment()
    def test_vara_develop_status(self):
        runner = CliRunner()
        # currently, status does nothing if no subprojects are specified.
        result = runner.invoke(driver_develop.main, ["szzunleashed", "status"])
        self.assertEqual(0, result.exit_code, result.exception)
