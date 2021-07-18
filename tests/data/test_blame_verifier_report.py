"""Test blame verifier reports."""

import unittest
from pathlib import Path

from varats.data.reports.blame_verifier_report import (
    BlameVerifierReportNoOpt,
    BlameVerifierReportOpt,
)
from varats.report.report import FileStatusExtension


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

        cls.test_result_file_path_no_opt = Path(
            __file__
        ).parent / "../TEST_INPUTS/results/gravity/BVR_NoOpt-gravity-gravity-" \
                   "b51227de55_8bc2ac4c-b6e3-43d1-aff9-c6b32126b155_success.txt"

        cls.test_result_file_path_opt = Path(
            __file__
        ).parent / "../TEST_INPUTS/results/gravity/BVR_Opt-gravity-gravity-" \
                   "b51227de55_5f696090-edcc-433e-9dda-a55718f0c02d_success.txt"

        cls.test_bvr_no_opt = BlameVerifierReportNoOpt(
            Path(cls.test_result_file_path_no_opt)
        )

        cls.test_bvr_opt = BlameVerifierReportOpt(
            Path(cls.test_result_file_path_opt)
        )

        cls.mock_successes_opt = 16082
        cls.mock_failures_opt = 50604
        cls.mock_undetermined_opt = 1439
        cls.mock_total_opt = 66686

        cls.mock_successes_no_opt = 108455
        cls.mock_failures_no_opt = 273
        cls.mock_undetermined_no_opt = 0
        cls.mock_total_no_opt = 108728

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
            extension_type=FileStatusExtension.SUCCESS,
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
            extension_type=FileStatusExtension.SUCCESS,
            file_ext=self.test_file_ext
        )

        # Then
        self.assertEqual(self.mock_file_name, actual)

    def test_parse_verifier_results_no_opt(self):
        """Test if the number of successful, failed, undetermined and total
        annotations of the BlameMDVerifier without optimization are correctly
        parsed from the result file."""

        actual_successes = self.test_bvr_no_opt.get_successful_annotations()
        actual_failures = self.test_bvr_no_opt.get_failed_annotations()
        actual_undetermined = self.test_bvr_no_opt.get_undetermined_annotations(
        )
        actual_total = self.test_bvr_no_opt.get_total_annotations()

        self.assertEqual(self.mock_successes_no_opt, actual_successes)
        self.assertEqual(self.mock_failures_no_opt, actual_failures)
        self.assertEqual(self.mock_undetermined_no_opt, actual_undetermined)
        self.assertEqual(self.mock_total_no_opt, actual_total)

    def test_parse_verifier_results_opt(self):
        """Test if the number of successful, failed, undetermined and total
        annotations of the BlameMDVerifier with optimization are correctly
        parsed from the result file."""

        actual_successes = self.test_bvr_opt.get_successful_annotations()
        actual_failures = self.test_bvr_opt.get_failed_annotations()
        actual_undetermined = self.test_bvr_opt.get_undetermined_annotations()
        actual_total = self.test_bvr_opt.get_total_annotations()

        self.assertEqual(self.mock_successes_opt, actual_successes)
        self.assertEqual(self.mock_failures_opt, actual_failures)
        self.assertEqual(self.mock_undetermined_opt, actual_undetermined)
        self.assertEqual(self.mock_total_opt, actual_total)
