"""Test VaRA report."""

import unittest

from varats.data.reports.commit_report import CommitReport as CR
from varats.data.reports.empty_report import EmptyReport
from varats.report.report import FileStatusExtension, MetaReport, ReportFilename


class TestFileStatusExtension(unittest.TestCase):
    """Test basic FileStatusExtension functionality."""

    def test_status_extension(self):
        """"""
        self.assertEqual(
            FileStatusExtension.Success.get_status_extension(), "success"
        )

    def test_physical_stati(self):
        """Check if the correct stati are marked as physical."""
        phy_stati = FileStatusExtension.get_physical_file_statuses()

        self.assertTrue(FileStatusExtension.Success in phy_stati)
        self.assertTrue(FileStatusExtension.Failed in phy_stati)
        self.assertTrue(FileStatusExtension.CompileError in phy_stati)

        self.assertFalse(FileStatusExtension.Missing in phy_stati)
        self.assertFalse(FileStatusExtension.Blocked in phy_stati)

        self.assertEqual(len(phy_stati), 3)

    def test_virtual_stati(self):
        """Check if the correct stati are marked as virtual."""
        virt_stati = FileStatusExtension.get_virtual_file_statuses()

        self.assertFalse(FileStatusExtension.Success in virt_stati)
        self.assertFalse(FileStatusExtension.Failed in virt_stati)
        self.assertFalse(FileStatusExtension.CompileError in virt_stati)

        self.assertTrue(FileStatusExtension.Missing in virt_stati)
        self.assertTrue(FileStatusExtension.Blocked in virt_stati)

        self.assertEqual(len(virt_stati), 2)

    def test_wrong_status_lookup(self):
        """Check we correctly handle error cases where a wrong status is looked
        up."""
        self.assertRaises(
            ValueError, FileStatusExtension.get_file_status_from_str,
            'HansDampf'
        )


class TestReportFilename(unittest.TestCase):
    """Test basic TestReportFilename functionality."""

    @classmethod
    def setUpClass(cls):
        """Setup file and CommitReport."""
        cls.raw_filename = (
            "CR-foo-foo-7bb9ef5f8c_"
            "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be_"
            "success.txt"
        )
        cls.report_filename = ReportFilename(cls.raw_filename)

    def test_filename(self):
        """Tests if filename access works."""
        self.assertEqual(self.report_filename.filename, self.raw_filename)

    def test_status_success(self):
        """Tests if status success works."""
        self.assertTrue(self.report_filename.has_status_success())

    def test_status_failed(self):
        """Tests if status failed works."""
        self.assertFalse(self.report_filename.has_status_failed())

    def test_status_compileerror(self):
        """Tests if status compileerror works."""
        self.assertFalse(self.report_filename.has_status_compileerror())

    def test_status_missing(self):
        """Tests if status missing works."""
        self.assertFalse(self.report_filename.has_status_missing())

    def test_status_blocked(self):
        """Tests if status blocked works."""
        self.assertFalse(self.report_filename.has_status_blocked())

    def test_is_result_file(self):
        """Tests if the filename was a correct result filename."""
        self.assertTrue(self.report_filename.is_result_file())

    def test_accessors(self):
        """Tests if the different accessor functions work."""
        self.assertEqual(self.report_filename.commit_hash, "7bb9ef5f8c")
        self.assertEqual(self.report_filename.shorthand, "CR")
        self.assertEqual(
            self.report_filename.file_status, FileStatusExtension.Success
        )


class TestMetaReport(unittest.TestCase):
    """Test basic CommitReport functionality."""

    @classmethod
    def setUpClass(cls):
        """Setup file and CommitReport."""
        cls.success_filename_cr = (
            "CR-foo-foo-7bb9ef5f8c_"
            "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be_"
            "success.txt"
        )
        cls.success_filename = (
            "EMPTY-foo-foo-7bb9ef5f8c_"
            "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be_"
            "success.txt"
        )
        cls.fail_filename = (
            "EMPTY-foo-foo-7bb9ef5f8c_"
            "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be_"
            "failed.txt"
        )
        cls.supplementary_filename = (
            "CR-SUPPL-foo-foo-7bb9ef5f8c_"
            "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be_test.txt"
        )

    def test_report_type_lookup(self):
        """Check if we can lookup report types with file names."""
        self.assertEqual(
            MetaReport.lookup_report_type_from_file_name(
                self.success_filename_cr
            ), MetaReport.REPORT_TYPES['CommitReport']
        )
        self.assertEqual(
            MetaReport.
            lookup_report_type_from_file_name("some_wrong_file_path"), None
        )
        self.assertEqual(
            MetaReport.lookup_report_type_from_file_name(
                "NONEXISTINGSHORTHAND-foo-foo-7bb9ef5f8c_"
                "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be_"
                "success.txt"
            ), None
        )

    def test_is_result_file(self):
        """Check if the result file matcher works."""
        self.assertTrue(ReportFilename(self.success_filename).is_result_file())
        self.assertTrue(ReportFilename(self.fail_filename).is_result_file())
        self.assertFalse(
            ReportFilename(self.success_filename.replace("_",
                                                         "")).is_result_file()
        )
        self.assertFalse(
            ReportFilename(self.fail_filename.replace("-", "")).is_result_file()
        )

    def test_is_supplementary_result_file(self):
        """Check if the supplementary result file matcher works."""
        self.assertTrue(
            MetaReport.is_result_file_supplementary(
                self.supplementary_filename
            )
        )
        self.assertFalse(
            MetaReport.is_result_file_supplementary(
                self.supplementary_filename.replace("_", "")
            )
        )
        self.assertFalse(
            ReportFilename(self.supplementary_filename).is_result_file()
        )

    def test_file_status(self):
        """Check if the correct file status is returned for MetaReport names."""
        self.assertTrue(
            ReportFilename(self.success_filename).has_status_success()
        )
        self.assertFalse(
            ReportFilename(self.fail_filename).has_status_success()
        )

        self.assertTrue(ReportFilename(self.fail_filename).has_status_failed())
        self.assertFalse(
            ReportFilename(self.success_filename).has_status_failed()
        )

    def test_get_commit(self):
        """Check if the correct commit hash is returned."""
        self.assertEqual(
            ReportFilename(self.success_filename).commit_hash, "7bb9ef5f8c"
        )
        self.assertEqual(
            ReportFilename(self.fail_filename).commit_hash, "7bb9ef5f8c"
        )

    def test_get_commit_supplementary(self):
        """Check if the correct commit hash is returned."""
        self.assertEqual(
            MetaReport.get_commit_hash_from_supplementary_result_file(
                self.supplementary_filename
            ), "7bb9ef5f8c"
        )

    def test_get_info_type_supplementary(self):
        """Check if the correct info_type is returned."""
        self.assertEqual(
            MetaReport.get_info_type_from_supplementary_result_file(
                self.supplementary_filename
            ), "test"
        )

    def test_file_name_creation(self):
        """Check if file names are created correctly."""
        self.assertEqual(
            EmptyReport.get_file_name(
                "foo", "foo", "7bb9ef5f8c",
                "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be",
                FileStatusExtension.Success
            ), self.success_filename
        )

        self.assertEqual(
            EmptyReport.get_file_name(
                "foo", "foo", "7bb9ef5f8c",
                "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be",
                FileStatusExtension.Failed
            ), self.fail_filename
        )

    def test_supplementary_file_name_creation(self):
        """Check if file names are created correctly."""
        self.assertEqual(
            CR.get_supplementary_file_name(
                "foo", "foo", "7bb9ef5f8c",
                "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be", "test", "txt"
            ), self.supplementary_filename
        )
