"""Test paper config tool."""
import unittest
import unittest.mock as mock
from io import StringIO
from pathlib import Path

from tests.test_utils import run_in_test_environment
from varats.paper_mgmt.paper_config import load_paper_config
from varats.tools.driver_paper_config import _pc_list, _pc_set
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
    @mock.patch('sys.stdout', new_callable=StringIO)
    def test_vara_pc_list(self, stdout):
        """Test the vara-pc list subcommand."""

        paper_configs = ["foo", "bar", "baz"]
        pc_path = Path(vara_cfg()["paper_config"]["folder"].value)
        for pc in paper_configs:
            (pc_path / pc).mkdir()
        vara_cfg()["paper_config"]["current_config"] = "foo"
        load_paper_config()
        _pc_list({})
        output = stdout.getvalue()
        self.assertEqual(
            "Found the following paper_configs:\nbar\nbaz\nfoo *\n", output
        )

    @run_in_test_environment()
    @mock.patch('builtins.input')
    @mock.patch('sys.stdout', new_callable=StringIO)
    def test_vara_pc_select(self, stdout, stdin):
        """Test the vara-pc select subcommand."""

        stdin.return_value = "1"
        paper_configs = ["foo", "bar", "baz"]
        pc_path = Path(vara_cfg()["paper_config"]["folder"].value)
        for pc in paper_configs:
            (pc_path / pc).mkdir()
        vara_cfg()["paper_config"]["current_config"] = "foo"
        load_paper_config()
        _pc_set({})
        output = stdout.getvalue()
        self.assertEqual("0. bar\n1. baz\n2. foo *\n", output)
        self.assertEqual(
            "baz",
            vara_cfg()["paper_config"]["current_config"].value
        )
