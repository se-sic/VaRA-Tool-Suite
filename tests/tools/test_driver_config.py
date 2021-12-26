"""Test config tool."""
import unittest

from click.testing import CliRunner

from tests.test_utils import run_in_test_environment
from varats.tools import driver_config
from varats.utils.settings import vara_cfg, save_config


class TestDriverConfig(unittest.TestCase):
    """Tests for the driver_config module."""

    @run_in_test_environment()
    def test_vara_config_set(self):
        runner = CliRunner()
        vara_cfg()["artefacts"]["artefacts_dir"] = "test"
        save_config()
        runner.invoke(
            driver_config.main, ["set", "artefacts/artefacts_dir=artefacts"]
        )
        self.assertEqual(
            "artefacts",
            vara_cfg()["artefacts"]["artefacts_dir"].value
        )
