"""Test paper config tool."""
import unittest
import unittest.mock as mock
from io import StringIO
from pathlib import Path

from click.testing import CliRunner

from tests.test_utils import run_in_test_environment
from varats.paper_mgmt.paper_config import load_paper_config
from varats.tools import driver_paper_config
from varats.utils.settings import vara_cfg


class PaperConfigMock():
    """PaperConfig mock class."""

    def __init__(self, folder_path: Path) -> None:
        self.__path = folder_path

    @property
    def path(self) -> Path:
        """Path to the paper config folder."""
        return self.__path


def _create_paper_config_mock(path: Path):
    return PaperConfigMock(path)


class TestDriverPaperConfig(unittest.TestCase):
    """Tests for the driver_paper_config module."""

    @run_in_test_environment()
    def test_vara_pc_create(self):
        """Test the vara-pc create subcommand."""
        runner = CliRunner()
        runner.invoke(driver_paper_config.main, ["create", "foo"])
        paper_config = Path(
            vara_cfg()["paper_config"]["folder"].value + "/" + "foo"
        )
        self.assertTrue(paper_config.exists())
        self.assertEqual("foo",
                         vara_cfg()["paper_config"]["current_config"].value
        )

    @run_in_test_environment()
    @mock.patch('sys.stdout', new_callable=StringIO)
    def test_vara_pc_list(self, stdout):
        """Test the vara-pc list subcommand."""
        runner = CliRunner()
        paper_configs = ["foo", "bar", "baz"]
        pc_path = Path(vara_cfg()["paper_config"]["folder"].value)
        for pc in paper_configs:
            (pc_path / pc).mkdir()
        vara_cfg()["paper_config"]["current_config"] = "foo"
        result = runner.invoke(driver_paper_config.main, ["list"])
        self.assertEqual(
            "Found the following paper_configs:\nbar\nbaz\nfoo *\n",
            result.output
        )

    @run_in_test_environment()
    def test_vara_pc_select(self):
        """Test the vara-pc select subcommand."""
        runner = CliRunner()
        paper_configs = ["foo", "bar", "baz"]
        pc_path = Path(vara_cfg()["paper_config"]["folder"].value)
        for pc in paper_configs:
            (pc_path / pc).mkdir()
        vara_cfg()["paper_config"]["current_config"] = "foo"
        load_paper_config()
        result = runner.invoke(driver_paper_config.main, ["select"], input="1")
        assert not result.exception
        self.assertEqual("0. bar\n1. baz\n2. foo *\n", result.output)
        self.assertEqual(
            "baz",
            vara_cfg()["paper_config"]["current_config"].value
        )
