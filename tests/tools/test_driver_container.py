"""Test varats container tool."""
import unittest
import unittest.mock as mock
from pathlib import Path

from click.testing import CliRunner

from tests.test_utils import run_in_test_environment
from varats.tools import driver_container
from varats.utils.settings import vara_cfg, bb_cfg


class TestDriverContainer(unittest.TestCase):
    """Tests for the driver_container module."""

    @run_in_test_environment()
    def test_container_select(self) -> None:
        runner = CliRunner()
        vara_cfg()["container"]["research_tool"] = None
        result = runner.invoke(driver_container.main, ["select", "-t", "vara"])
        self.assertEqual(0, result.exit_code, result.exception)
        self.assertEqual("vara", vara_cfg()["container"]["research_tool"].value)

    @run_in_test_environment()
    @mock.patch("varats.tools.driver_container.export_base_images")
    @mock.patch("varats.tools.driver_container.create_base_images")
    def test_prepare_slurm(self, mock_create, mock_export) -> None:
        runner = CliRunner()
        bb_root = vara_cfg()["benchbuild_root"].value
        node_dir = "/tmp/foo"
        export_dir = "export"
        vara_cfg()["container"]["research_tool"] = None
        result = runner.invoke(
            driver_container.main, [
                "prepare-slurm", "-i", "DEBIAN_10", "-t", "vara",
                "--export-dir", export_dir, "--node-dir", node_dir
            ]
        )
        self.assertEqual(0, result.exit_code, result.exception)

        # check vara config
        self.assertEqual("vara", vara_cfg()["container"]["research_tool"].value)

        # check slurm config
        self.assertEqual(
            f"{bb_root}/slurm_container.sh.inc",
            bb_cfg()["slurm"]["template"].value
        )
        self.assertTrue(Path(f"{bb_root}/slurm_container.sh.inc").is_file())

        # check bb container config
        self.assertEqual(
            f"{node_dir}/containers/lib",
            bb_cfg()["container"]["root"].value
        )
        self.assertEqual(
            f"{node_dir}/containers/run",
            bb_cfg()["container"]["runroot"].value
        )
        self.assertEqual(export_dir, bb_cfg()["container"]["export"].value)
        self.assertEqual(export_dir, bb_cfg()["container"]["import"].value)
        self.assertTrue(Path(export_dir).is_dir())
