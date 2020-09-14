"""Test paper config tool."""
import tempfile
import unittest
import unittest.mock as mock
from io import StringIO
from pathlib import Path

from tests.test_utils import replace_config
from varats.paper import paper_config
from varats.tools.driver_paper_config import _pc_list, _pc_set


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

    @mock.patch('sys.stdout', new_callable=StringIO)
    @mock.patch('varats.paper.paper_config.PaperConfig')
    @mock.patch('varats.tools.driver_paper_config._get_paper_configs')
    def test_vara_pc_list(
        self, mock_get_paper_configs, mock_paper_config, stdout
    ):
        """Test the vara-pc list subcommand."""

        mock_get_paper_configs.return_value = ["foo", "bar", "baz"]
        mock_paper_config.return_value.path = Path("foo")
        with replace_config() as config:
            config["paper_config"]["current_config"] = "foo"
            paper_config._G_PAPER_CONFIG = paper_config.PaperConfig(Path("foo"))
            _pc_list({})
            output = stdout.getvalue()
            self.assertEqual(
                "Found the following paper_configs:\nfoo *\nbar\nbaz\n", output
            )

    @mock.patch('builtins.input')
    @mock.patch('sys.stdout', new_callable=StringIO)
    @mock.patch(
        'varats.paper.paper_config.PaperConfig',
        side_effect=_create_paper_config_mock
    )
    @mock.patch('varats.tools.driver_paper_config._get_paper_configs')
    # pylint: ignore=unused-argument
    def test_vara_pc_select(
        self, mock_get_paper_configs, mock_paper_config, stdout, stdin
    ):
        """Test the vara-pc select subcommand."""

        stdin.return_value = "1"
        mock_get_paper_configs.return_value = ["foo", "bar", "baz"]
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            pc_path = tmppath / "paper_configs"
            pc_path.mkdir()
            for pc in mock_get_paper_configs.return_value:
                (pc_path / pc).mkdir()
            with replace_config(tmp_path=tmppath) as config:
                config["paper_config"]["folder"] = str(pc_path)
                config["paper_config"]["current_config"] = "foo"
                paper_config._G_PAPER_CONFIG = paper_config.PaperConfig(
                    Path("foo")
                )
                _pc_set({})
                output = stdout.getvalue()
                self.assertEqual(output, "0. foo *\n1. bar\n2. baz\n")
                self.assertEqual(
                    "bar", config["paper_config"]["current_config"].value
                )
