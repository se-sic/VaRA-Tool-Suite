"""Test varats gen benchbuild config module."""
import os
import unittest
from pathlib import Path

from click.testing import CliRunner

from tests.test_utils import run_in_test_environment
from varats.tools import driver_gen_benchbuild_config
from varats.utils.settings import vara_cfg


class TestDriverGenBenchbuildConfig(unittest.TestCase):
    """Tests for the driver_gen_benchbuild_config module."""

    @run_in_test_environment()
    def test_gen_bbconfig(self):
        """basic tests for the `gen-bbconfig` command."""
        runner = CliRunner()
        os.remove(
            Path(vara_cfg()["benchbuild_root"].value + "/.benchbuild.yml")
        )
        runner.invoke(driver_gen_benchbuild_config.main, [])
        self.assertTrue(
            Path(vara_cfg()["benchbuild_root"].value +
                 "/.benchbuild.yml").exists()
        )
