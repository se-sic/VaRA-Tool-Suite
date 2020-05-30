"""Test blame verifier reports."""

import unittest

from varats.data.report import FileStatusExtension
from varats.data.reports import blame_verifier_report as BVR


class TestBlameVerifierReport(unittest.TestCase):
    """Test if a blame verifier report is correctly reconstructed from .txt."""

    def test_get_file_name_opt(self):
        """Test if the file name is correctly built with the opt extension."""
        # Given
        test_shorthand = "BVR_Opt"
        test_project_name = "testProject"
        test_binary_name = "testBinary"
        test_project_version = "testProjectVersion1"
        test_project_uuid = "00000000-0000-0000-0000-000000000001"
        test_extension_type = 'success'
        test_file_ext = ".txt"

        mock_file_name = f"{test_shorthand}-{test_project_name}" \
                         f"-{test_binary_name}-{test_project_version}_" \
                         f"{test_project_uuid}_{test_extension_type}" \
                         f"{test_file_ext}"

        # When
        actual = BVR.BlameVerifierReportOpt.get_file_name(
            project_name=test_project_name,
            binary_name=test_binary_name,
            project_version=test_project_version,
            project_uuid=test_project_uuid,
            extension_type=FileStatusExtension.Success,
            file_ext=test_file_ext
        )

        # Then
        self.assertEqual(mock_file_name, actual)

    def test_get_file_name_no_opt(self):
        """Test if the file name is correctly built without the opt
        extension."""
        # Given
        test_shorthand = "BVR_NoOpt"
        test_project_name = "testProject"
        test_binary_name = "testBinary"
        test_project_version = "testProjectVersion1"
        test_project_uuid = "00000000-0000-0000-0000-000000000001"
        test_extension_type = 'failed'
        test_file_ext = ".txt"

        mock_file_name = f"{test_shorthand}-{test_project_name}" \
                         f"-{test_binary_name}-{test_project_version}_" \
                         f"{test_project_uuid}_{test_extension_type}" \
                         f"{test_file_ext}"

        # When
        actual = BVR.BlameVerifierReportNoOpt.get_file_name(
            project_name=test_project_name,
            binary_name=test_binary_name,
            project_version=test_project_version,
            project_uuid=test_project_uuid,
            extension_type=FileStatusExtension.Failed,
            file_ext=test_file_ext
        )

        # Assert
        self.assertEqual(mock_file_name, actual)
