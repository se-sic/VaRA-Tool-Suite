import unittest
import mock

class ExampleTestCase(unittest.TestCase):

    def test_foo(self):
        pass


def function_under_test(file_path):
    with open(file_path) as f:
        txt = f.read()
        print(txt)
        return txt


class MyTestCase(unittest.TestCase):

    @mock.patch("builtins.open", create=True)
    def test_function_under_test(self, mock_open):
        mock_open.side_effect = [
            mock.mock_open(read_data="FileContents").return_value,
        ]

        self.assertEqual("FileContents", function_under_test("fake_file_path"))
        mock_open.assert_called_once_with("fake_file_path")
