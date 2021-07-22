"""Test VaRA report."""

import unittest

from varats.data.reports.blame_report import BlameReport as BR
from varats.data.reports.commit_report import CommitReport as CR
from varats.data.reports.empty_report import EmptyReport
from varats.report.gnu_time_report import TimeReport as TR
from varats.report.report import (
    FileStatusExtension,
    BaseReport,
    ReportFilename,
    ReportSpecification,
)
from varats.utils.git_util import ShortCommitHash


class TestFileStatusExtension(unittest.TestCase):
    """Test basic FileStatusExtension functionality."""

    def test_status_extension(self):
        """"""
        self.assertEqual(
            FileStatusExtension.SUCCESS.get_status_extension(), "success"
        )

    def test_physical_stati(self):
        """Check if the correct stati are marked as physical."""
        phy_stati = FileStatusExtension.get_physical_file_statuses()

        self.assertTrue(FileStatusExtension.SUCCESS in phy_stati)
        self.assertTrue(FileStatusExtension.FAILED in phy_stati)
        self.assertTrue(FileStatusExtension.COMPILE_ERROR in phy_stati)

        self.assertFalse(FileStatusExtension.MISSING in phy_stati)
        self.assertFalse(FileStatusExtension.BLOCKED in phy_stati)

        self.assertEqual(len(phy_stati), 3)

    def test_virtual_stati(self):
        """Check if the correct stati are marked as virtual."""
        virt_stati = FileStatusExtension.get_virtual_file_statuses()

        self.assertFalse(FileStatusExtension.SUCCESS in virt_stati)
        self.assertFalse(FileStatusExtension.FAILED in virt_stati)
        self.assertFalse(FileStatusExtension.COMPILE_ERROR in virt_stati)

        self.assertTrue(FileStatusExtension.MISSING in virt_stati)
        self.assertTrue(FileStatusExtension.BLOCKED in virt_stati)

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
        cls.correct_UUID = "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be"
        cls.raw_filename = (
            "CR-foo-foo-7bb9ef5f8c_"
            f"{cls.correct_UUID}_"
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
        self.assertEqual(
            self.report_filename.commit_hash, ShortCommitHash("7bb9ef5f8c")
        )
        self.assertEqual(self.report_filename.shorthand, "CR")
        self.assertEqual(
            self.report_filename.file_status, FileStatusExtension.SUCCESS
        )

    def test_get_uuid(self):
        """Check if we can extract the UUID from a filename."""
        self.assertEqual(self.report_filename.uuid, self.correct_UUID)


class TestBaseReport(unittest.TestCase):
    """Test basic BaseReport functionality."""

    @classmethod
    def setUpClass(cls):
        """Setup report file paths."""
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

    def test_report_type_lookup(self):
        """Check if we can lookup report types with file names."""
        self.assertEqual(
            BaseReport.lookup_report_type_from_file_name(
                self.success_filename_cr
            ), BaseReport.REPORT_TYPES['CommitReport']
        )
        self.assertEqual(
            BaseReport.
            lookup_report_type_from_file_name("some_wrong_file_path"), None
        )
        self.assertEqual(
            BaseReport.lookup_report_type_from_file_name(
                "NONEXISTINGSHORTHAND-foo-foo-7bb9ef5f8c_"
                "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be_"
                "success.txt"
            ), None
        )

    def test_report_type_lookup_by_shorthand(self):
        """Check if we can lookup report types with a report shorthand."""
        self.assertEqual(
            BaseReport.lookup_report_type_by_shorthand("CR"),
            BaseReport.REPORT_TYPES['CommitReport']
        )
        self.assertEqual(
            BaseReport.lookup_report_type_by_shorthand("NONEXISTINGSHORTHAND"),
            None
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

    def test_file_status(self):
        """Check if the correct file status is returned for BaseReport names."""
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
            ReportFilename(self.success_filename).commit_hash,
            ShortCommitHash("7bb9ef5f8c")
        )
        self.assertEqual(
            ReportFilename(self.fail_filename).commit_hash,
            ShortCommitHash("7bb9ef5f8c")
        )

    def test_file_name_creation(self):
        """Check if file names are created correctly."""
        self.assertEqual(
            EmptyReport.get_file_name(
                "foo", "foo", "7bb9ef5f8c",
                "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be",
                FileStatusExtension.SUCCESS
            ), self.success_filename
        )

        self.assertEqual(
            EmptyReport.get_file_name(
                "foo", "foo", "7bb9ef5f8c",
                "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be",
                FileStatusExtension.FAILED
            ), self.fail_filename
        )


class TestRepoprtSpecification(unittest.TestCase):
    """Test basic ReportSpecification functionality."""

    def test_wrong_spec_setup(self):
        """Check if we correctly reject empty specs."""
        self.assertRaises(AssertionError, ReportSpecification)

    def test_spec_properties(self):
        """Check if the basic properties work."""
        spec = ReportSpecification(CR, BR)

        # First report should be the main report
        self.assertEqual(spec.main_report, CR)

        self.assertListEqual(spec.report_types, [CR, BR])

    def test_if_report_is_in_spec(self):
        """Check if we correctly verify that a report is in the spec."""
        spec = ReportSpecification(CR, BR)

        self.assertTrue(spec.in_spec(CR))
        self.assertTrue(spec.in_spec(BR))
        self.assertFalse(spec.in_spec(TR))

        self.assertTrue(CR in spec)
        self.assertTrue(BR in spec)
        self.assertFalse(TR in spec)
