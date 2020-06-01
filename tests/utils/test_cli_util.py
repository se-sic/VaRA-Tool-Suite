"""Testing module for cli utils."""

import tempfile
import unittest
from pathlib import Path

import mock

from tests.test_utils import replace_config
from varats.tools.research_tools.phasar import Phasar
from varats.tools.research_tools.vara import VaRA
from varats.utils.cli_util import get_research_tool_type, get_research_tool


class ResearchToolUtils(unittest.TestCase):
    """Testing different cli utility functions."""

    def test_research_tool_type_lookup(self):
        """Checks if names are correctly mapped to ``ResearchTool`` types."""
        self.assertEqual(get_research_tool_type("vara"), VaRA)
        self.assertEqual(get_research_tool_type("phasar"), Phasar)

    @mock.patch('varats.tools.research_tools.vara.save_config')
    def test_research_tool_accessor_default(self, _):
        """Checks if the source_location of a ``ResearchTool`` is set to the
        correct default."""
        tmp_path = tempfile.TemporaryDirectory()
        with replace_config() as vara_cfg:
            vara_cfg["config_file"] = str(tmp_path.name + "/dummy.yml")
            vara = get_research_tool("vara")
            self.assertTrue(vara.has_source_location())
            self.assertEqual(
                vara.source_location().relative_to(Path(tmp_path.name)),
                Path("tools_src")
            )

        tmp_path.cleanup()

    @mock.patch('varats.tools.research_tools.vara.save_config')
    def test_research_tool_accessor_custom(self, _):
        """Checks if the source_location of a ``ResearchTool`` is correctly set
        if configured by the user."""
        with replace_config() as _:
            configured_location = Path("foo/bar/bazz")
            vara = get_research_tool("vara", configured_location)
            self.assertTrue(vara.has_source_location())
            self.assertEqual(vara.source_location(), configured_location)

    @mock.patch('varats.tools.research_tools.vara.save_config')
    def test_research_tool_accessor_existing(self, _):
        """Checks if the source_location of a ``ResearchTool`` is correctly
        resetup from the current config."""
        with replace_config() as vara_cfg:
            configured_location = Path("foo/bar/bazz")
            vara_cfg["vara"]["llvm_source_dir"] = str(configured_location)
            vara = get_research_tool("vara")
            self.assertTrue(vara.has_source_location())
            self.assertEqual(vara.source_location(), configured_location)
