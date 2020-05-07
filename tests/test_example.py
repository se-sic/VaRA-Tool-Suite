"""Test example file that can be used as orientation."""
import unittest

import mock


class ExampleTestCase(unittest.TestCase):
    """An example for how to create a test case."""

    def test_foo(self):
        """How create a test."""


def function_under_test(file_path):
    """Example function with IO to tests."""
    with open(file_path) as opened_filed:
        txt = opened_filed.read()
        print(txt)
        return txt


class MyTestCase(unittest.TestCase):
    """An example for how to create a test case that needs mocking because of
    file IO."""

    @mock.patch("builtins.open", create=True)
    def test_function_under_test(self, mock_open):
        """Test function with mocked method for file access."""
        mock_open.side_effect = [
            mock.mock_open(read_data="FileContents").return_value,
        ]

        self.assertEqual("FileContents", function_under_test("fake_file_path"))
        mock_open.assert_called_once_with("fake_file_path")
