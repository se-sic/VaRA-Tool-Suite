"""Testing module for cli utils."""

import unittest
import unittest.mock as mock
from pathlib import Path

from tests.test_utils import run_in_test_environment, test_environment
from varats.tools.research_tools.phasar import Phasar
from varats.tools.research_tools.vara import VaRA
from varats.tools.tool_util import get_research_tool_type, get_research_tool
from varats.utils.settings import vara_cfg


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
        with test_environment() as tmp_path:
            vara_cfg()["config_file"] = tmp_path / "dummy.yml"
            vara_cfg()["vara"]["llvm_source_dir"] = tmp_path / "tools_src"
            vara = get_research_tool("vara")
            self.assertTrue(vara.has_source_location())
            self.assertEqual(
                vara.source_location().relative_to(Path(tmp_path)),
                Path("tools_src")
            )

    @run_in_test_environment
    @mock.patch('varats.tools.research_tools.vara.save_config')
    def test_research_tool_accessor_custom(self, _):
        """Checks if the source_location of a ``ResearchTool`` is correctly set
        if configured by the user."""
        configured_location = Path("foo/bar/bazz")
        vara = get_research_tool("vara", configured_location)
        self.assertTrue(vara.has_source_location())
        self.assertEqual(vara.source_location(), configured_location)

    @run_in_test_environment
    @mock.patch('varats.tools.research_tools.vara.save_config')
    def test_research_tool_accessor_existing(self, _):
        """Checks if the source_location of a ``ResearchTool`` is correctly
        resetup from the current config."""
        configured_location = Path("foo/bar/bazz")
        vara_cfg()["vara"]["llvm_source_dir"] = str(configured_location)
        vara = get_research_tool("vara")
        self.assertTrue(vara.has_source_location())
        self.assertEqual(vara.source_location(), configured_location)
