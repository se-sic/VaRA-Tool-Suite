"""
Test VaRA report.
"""

import unittest

from varats.data.report import FileStatusExtension, MetaReport
from varats.data.reports.empty_report import EmptyReport
from varats.data.reports.commit_report import CommitReport as CR


class TestMetaReport(unittest.TestCase):
    """
    Test basic CommitReport functionality.
    """

    @classmethod
    def setUpClass(cls):
        """
        Setup file and CommitReport
        """
        cls.success_filename_cr = ("CR-foo-foo-7bb9ef5f8c_"
                                   "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be_"
                                   "success.txt")
        cls.success_filename = ("EMPTY-foo-foo-7bb9ef5f8c_"
                                "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be_"
                                "success.txt")
        cls.fail_filename = ("EMPTY-foo-foo-7bb9ef5f8c_"
                             "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be_"
                             "failed.txt")
        cls.supplementary_filename = (
            "CR-SUPPL-foo-foo-7bb9ef5f8c_"
            "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be_test.txt")

    def test_report_type_lookup(self):
        """Check if we can lookup report types with file names."""
        self.assertEqual(
            MetaReport.lookup_report_type_from_file_name(
                self.success_filename_cr),
            MetaReport.REPORT_TYPES['CommitReport'])
        self.assertEqual(
            MetaReport.lookup_report_type_from_file_name(
                "some_wrong_file_path"), None)
        self.assertEqual(
            MetaReport.lookup_report_type_from_file_name(
                "NONEXISTINGSHORTHAND-foo-foo-7bb9ef5f8c_"
                "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be_"
                "success.txt"), None)

    def test_is_result_file(self):
        """Check if the result file matcher works"""
        self.assertTrue(MetaReport.is_result_file(self.success_filename))
        self.assertTrue(MetaReport.is_result_file(self.fail_filename))
        self.assertFalse(
            MetaReport.is_result_file(self.success_filename.replace("_", "")))
        self.assertFalse(
            MetaReport.is_result_file(self.fail_filename.replace("-", "")))

    def test_is_supplementary_result_file(self):
        """Check if the supplementary result file matcher works"""
        self.assertTrue(
            MetaReport.is_result_file_supplementary(
                self.supplementary_filename))
        self.assertFalse(
            MetaReport.is_result_file_supplementary(
                self.supplementary_filename.replace("_", "")))
        self.assertFalse(MetaReport.is_result_file(self.supplementary_filename))

    def test_file_status(self):
        """
        Check if the correct file status is returned for MetaReport names.
        """
        self.assertTrue(
            MetaReport.result_file_has_status_success(self.success_filename))
        self.assertFalse(
            MetaReport.result_file_has_status_success(self.fail_filename))

        self.assertTrue(
            MetaReport.result_file_has_status_failed(self.fail_filename))
        self.assertFalse(
            MetaReport.result_file_has_status_failed(self.success_filename))

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

    def test_get_commit_supplementary(self):
        """
        Check if the correct commit hash is returned.
        """
        self.assertEqual(
            MetaReport.get_commit_hash_from_supplementary_result_file(
                self.supplementary_filename), "7bb9ef5f8c")

    def test_get_info_type_supplementary(self):
        """
        Check if the correct info_type is returned.
        """
        self.assertEqual(
            MetaReport.get_info_type_from_supplementary_result_file(
                self.supplementary_filename), "test")

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

    def test_supplementary_file_name_creation(self):
        """
         Check if file names are created correctly.
        """
        self.assertEqual(
            CR.get_supplementary_file_name(
                "foo", "foo", "7bb9ef5f8c",
                "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be", "test", "txt"),
            self.supplementary_filename)
