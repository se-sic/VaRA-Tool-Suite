"""Test blame verifier reports."""

import unittest
from pathlib import Path

from varats.data.report import FileStatusExtension
from varats.data.reports.blame_verifier_report import (
    BlameVerifierReportNoOpt,
    BlameVerifierReportOpt,
    ResultType,
)


class TestBlameVerifierReport(unittest.TestCase):
    """Test if a blame verifier report is correctly reconstructed from .txt."""

    @classmethod
    def setUpClass(cls):
        """Setup example file name."""
        cls.test_project_name = "testProject"
        cls.test_binary_name = "testBinary"
        cls.test_project_version = "testyamlProjectVersion1"
        cls.test_project_uuid = "00000000-0000-0000-0000-000000000001"
        cls.test_extension_type = 'success'
        cls.test_file_ext = ".txt"

        cls.mock_file_name = f"-{cls.test_project_name}" \
                             f"-{cls.test_binary_name}-" \
                             f"{cls.test_project_version}_" \
                             f"{cls.test_project_uuid}_" \
                             f"{cls.test_extension_type}" \
                             f"{cls.test_file_ext}"

        cls.test_result_file_path = Path(
            __file__
        ).parent / "../TEST_INPUTS/results/gravity/BVR_Opt-gravity-gravity-" \
                   "b51227de55_5f696090-edcc-433e-9dda-a55718f0c02d_success.txt"

        cls.mock_successes = 16082
        cls.mock_failures = 50604
        cls.mock_total = 66686

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

    def test_parse_verifier_results_opt(self):
        """Test if the number of successful, failed and total comparisons of the
        BlameMDVerifier with optimization are correctly parsed from the result
        file."""
        # Given

        # When
        actual_successes = BlameVerifierReportOpt.parse_verifier_results(
            self.test_result_file_path, ResultType.SUCCESSES
        )
        actual_failures = BlameVerifierReportOpt.parse_verifier_results(
            self.test_result_file_path, ResultType.FAILURES
        )
        actual_total = BlameVerifierReportOpt.parse_verifier_results(
            self.test_result_file_path, ResultType.TOTAL
        )

        # Then
        self.assertEqual(self.mock_successes, actual_successes)
        self.assertEqual(self.mock_failures, actual_failures)
        self.assertEqual(self.mock_total, actual_total)

    def test_parse_verifier_results_no_opt(self):
        """Test if the number of successful, failed and total comparisons of the
        BlameMDVerifier with optimization are correctly parsed from the result
        file."""
        # Given

        # When
        actual_successes = BlameVerifierReportNoOpt.parse_verifier_results(
            self.test_result_file_path, ResultType.SUCCESSES
        )
        actual_failures = BlameVerifierReportNoOpt.parse_verifier_results(
            self.test_result_file_path, ResultType.FAILURES
        )
        actual_total = BlameVerifierReportNoOpt.parse_verifier_results(
            self.test_result_file_path, ResultType.TOTAL
        )

        # Then
        self.assertEqual(self.mock_successes, actual_successes)
        self.assertEqual(self.mock_failures, actual_failures)
        self.assertEqual(self.mock_total, actual_total)
