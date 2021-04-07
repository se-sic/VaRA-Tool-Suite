"""Test yaml utility functions."""
import unittest
from pathlib import Path

from varats.utils.yaml_util import get_path_to_test_inputs


class TestYamlUtils(unittest.TestCase):
    """Test functions to access, modify, and store yaml files."""

    def test_get_path_to_test_inputs(self) -> None:
        self.assertTrue(Path.exists(get_path_to_test_inputs()))
