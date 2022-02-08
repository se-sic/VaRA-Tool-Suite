"""Test varats container tool."""
import unittest
import unittest.mock as mock
from pathlib import Path

from click.testing import CliRunner

from tests.test_utils import run_in_test_environment
from varats.containers.containers import ImageBase
from varats.tools import driver_build_setup
from varats.tools.driver_build_setup import _build_in_container
from varats.tools.research_tools.vara_manager import BuildType
from varats.tools.tool_util import get_research_tool
from varats.utils.settings import vara_cfg


class TestDriverBuildsetup(unittest.TestCase):
    """Tests for the driver_build_setup module."""

    @run_in_test_environment()
    def test_init_config(self) -> None:
        config_path = Path(vara_cfg()["config_file"].value)
        if config_path.exists():
            config_path.unlink()
        self.assertFalse(config_path.exists())
        runner = CliRunner()
        result = runner.invoke(driver_build_setup.main, ["config"])
        self.assertEqual(0, result.exit_code, result.exception)
        self.assertTrue(config_path.exists())

    @run_in_test_environment()
    @mock.patch("varats.tools.driver_build_setup.run_container")
    @mock.patch("varats.tools.driver_build_setup.create_dev_image")
    def test_build_in_container(self, mock_create, mock_run) -> None:
        config_path = Path(vara_cfg()["config_file"].value).parent
        vara_cfg()["vara"]["llvm_source_dir"] = str(config_path / "tools_src")
        vara_cfg()["vara"]["llvm_install_dir"] = str(
            config_path / "tools" / "VaRA"
        )

        research_tool = get_research_tool("vara")
        image_base = ImageBase.DEBIAN_10
        build_type = BuildType.DEV

        _build_in_container(research_tool, image_base, build_type)

        mock_create.assert_called_with(image_base, research_tool)
        mock_run.assert_called_with(
            "localhost/debian:10_varats_vara_DEV", "build_VaRA", None, [
                "build",
                "vara",
                "--build-type=DEV",
                "--source-location=/varats_root/tools_src",
                "--install-prefix=/varats_root/tools/VaRA_DEBIAN_10",
                "--build-folder-suffix=DEBIAN_10",
            ]
        )
