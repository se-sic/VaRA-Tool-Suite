"""
Test VaRA report.
"""

import unittest

from varats.data.report import FileStatusExtension, MetaReport
from varats.data.reports.empty_report import EmptyReport


class TestMetaReport(unittest.TestCase):
    """
    Test basic CommitReport functionality.
    """

    @classmethod
    def setUpClass(cls):
        """
        Setup file and CommitReport
        """
        cls.success_filename = ("EMPTY-foo-foo-7bb9ef5f8c_"
                                "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be.yaml")
        cls.fail_filename = ("EMPTY-foo-foo-7bb9ef5f8c_"
                             "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be.failed")

    def test_is_result_file(self):
        """Check if the result file matcher works"""
        self.assertTrue(MetaReport.is_result_file(self.success_filename))
        self.assertTrue(MetaReport.is_result_file(self.fail_filename))
        self.assertFalse(
            MetaReport.is_result_file(self.success_filename.replace("_", "")))
        self.assertFalse(
            MetaReport.is_result_file(self.success_filename.replace("-", "")))
        self.assertFalse(
            MetaReport.is_result_file(self.success_filename.replace(".", "f")))

    def test_file_status(self):
        """
        Check if the correct file status is returned for MetaReport names.
        """
        self.assertTrue(
            MetaReport.is_result_file_success(self.success_filename))
        self.assertFalse(MetaReport.is_result_file_success(self.fail_filename))

        self.assertTrue(MetaReport.is_result_file_failed(self.fail_filename))
        self.assertFalse(
            MetaReport.is_result_file_failed(self.success_filename))

    def test_get_commit(self):
        """
        Check if the correct commit hash is returned.
        """
        self.assertEqual(
            MetaReport.get_commit_hash_from_result_file(self.success_filename),
            "7bb9ef5f8c")
        self.assertEqual(
            MetaReport.get_commit_hash_from_result_file(self.fail_filename),
            "7bb9ef5f8c")

    def test_file_name_creation(self):
        """
         Check if file names are created correctly.
        """
        self.assertEqual(
            EmptyReport.get_file_name("foo", "foo", "7bb9ef5f8c",
                                      "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be",
                                      FileStatusExtension.Success),
            self.success_filename)

        self.assertEqual(
            EmptyReport.get_file_name("foo", "foo", "7bb9ef5f8c",
                                      "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be",
                                      FileStatusExtension.Failed),
            self.fail_filename)
