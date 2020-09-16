"""Test the VersionHeader module."""
import unittest
import unittest.mock as mock

import yaml

import varats.base.version_header as vh


class TestVersionHeader(unittest.TestCase):
    """Test VersionHeaders generated from VaRA and added to yaml reports."""

    @classmethod
    def setUpClass(cls):
        """Setup parsed version header."""
        file_content = """
---
DocType:         CommitReport
Version:         3
...
"""

        with mock.patch(
            'builtins.open', new=mock.mock_open(read_data=file_content)
        ):
            with open('fake_file_path') as yaml_file:
                docs = yaml.safe_load(yaml_file)
                cls.version_header = vh.VersionHeader(docs)

    def test_if_fields_where_loaded_correctly(self):
        """Test if the file content was correctly loaded."""
        self.assertEqual(self.version_header.doc_type, "CommitReport")
        self.assertTrue(self.version_header.is_type("CommitReport"))

        self.assertEqual(self.version_header.version, 3)

    def test_exception_checkers(self):
        """Exception checkers should throw expections in cases where we would
        expect other values."""
        self.assertRaises(
            vh.WrongYamlFileType, self.version_header.raise_if_not_type,
            "FooReport"
        )
        self.assertRaises(
            vh.WrongYamlFileVersion,
            self.version_header.raise_if_version_is_less_than, 4
        )

    @unittest.mock.patch("builtins.open", create=True)
    def test_loading_of_wrong_yaml_doc(self, mock_open):
        """If we pass a wrong yaml document into VersionHeader we expect and
        Exception."""
        mock_open.side_effect = [
            mock.mock_open(read_data="""
---
Foo:            Bar
...
""").return_value,
        ]

        with open('fake_file_path') as yaml_file:
            docs = yaml.safe_load(yaml_file)
            self.assertRaises(vh.NoVersionHeader, vh.VersionHeader, docs)
