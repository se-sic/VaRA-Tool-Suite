"""Test blame verifier reports."""

import unittest

from varats.data.report import FileStatusExtension
from varats.data.reports.blame_verifier_report import (
    BlameVerifierReportNoOpt,
    BlameVerifierReportOpt,
)


class TestBlameVerifierReport(unittest.TestCase):
    """Test if a blame verifier report is correctly reconstructed from .txt."""

    @classmethod
    def setUpClass(cls):
        """Setup example file name."""
        cls.test_project_name = "testProject"
        cls.test_binary_name = "testBinary"
        cls.test_project_version = "testProjectVersion1"
        cls.test_project_uuid = "00000000-0000-0000-0000-000000000001"
        cls.test_extension_type = 'success'
        cls.test_file_ext = ".txt"

        cls.mock_file_name = f"-{cls.test_project_name}" \
                             f"-{cls.test_binary_name}-" \
                             f"{cls.test_project_version}_" \
                             f"{cls.test_project_uuid}_" \
                             f"{cls.test_extension_type}" \
                             f"{cls.test_file_ext}"

    def test_get_file_name_opt(self):
        """Test if the file name is correctly built with the opt extension."""
        # Given
        self.mock_file_name = f"BVR_Opt{self.mock_file_name}"

        # When
        actual = BlameVerifierReportOpt.get_file_name(
            project_name=self.test_project_name,
            binary_name=self.test_binary_name,
            project_version=self.test_project_version,
            project_uuid=self.test_project_uuid,
            extension_type=FileStatusExtension.Success,
            file_ext=self.test_file_ext
        )

        # Then
        self.assertEqual(self.mock_file_name, actual)

    def test_get_file_name_no_opt(self):
        """Test if the file name is correctly built without the opt
        extension."""
        # Given
        self.mock_file_name = f"BVR_NoOpt{self.mock_file_name}"

        # When
        actual = BlameVerifierReportNoOpt.get_file_name(
            project_name=self.test_project_name,
            binary_name=self.test_binary_name,
            project_version=self.test_project_version,
            project_uuid=self.test_project_uuid,
            extension_type=FileStatusExtension.Success,
            file_ext=self.test_file_ext
        )

        # Then
        self.assertEqual(self.mock_file_name, actual)
