"""Test research tool vara."""

import unittest
import unittest.mock as mock

from varats.tools.tool_util import get_research_tool


class TestVara(unittest.TestCase):
    """Test the research tool implementation for VaRA."""

    @classmethod
    def setUp(cls) -> None:
        """Set up tools to test vara."""
        cls.research_tool_vara = get_research_tool("vara")

    @mock.patch(
        'varats.tools.research_tools.research_tool.SubProject.get_branches'
    )
    @mock.patch('varats.tools.research_tools.vara.VaRACodeBase.get_tags')
    @mock.patch('varats.tools.research_tools.vara.VaRACodeBase.fetch')
    def test_find_highest_sub_prj_version(
        self, _, mock_get_tags, mock_get_branches_subproject
    ) -> None:
        """Test if the major release version regex matches the highest
        version."""
        mock_tag_list = [
            "foo-9.0.0", "90.0-bar", "release_90", "vara-4.2.0", "vara-4.2.9",
            "vara-3.9.0"
        ]
        mock_branch_name_list = [
            "foobar-100-dev", "origin/vara-43-dev", "vara-42-dev",
            "vara-100-foo"
        ]

        mock_get_tags.return_value = mock_tag_list
        mock_get_branches_subproject.return_value = mock_branch_name_list

        highest_vara_version = \
            self.research_tool_vara.find_highest_sub_prj_version("VaRA")
        highest_llvm_version = \
            self.research_tool_vara.find_highest_sub_prj_version(
                "vara-llvm-project"
            )

        self.assertEqual(42, highest_vara_version)
        self.assertEqual(43, highest_llvm_version)
