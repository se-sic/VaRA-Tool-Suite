"""Test blame diff based commit-data metrics."""
import unittest
import unittest.mock as mock
from pathlib import Path
from tempfile import NamedTemporaryFile

from tests.paper.test_case_study import YAML_CASE_STUDY
from varats.data.databases.blame_diff_metrics_database import (
    id_from_paths,
    timestamp_from_paths,
    compare_timestamps,
    build_report_files_tuple,
)
from varats.paper.case_study import load_case_study_from_file
from varats.utils.yaml_util import get_path_to_test_inputs


class TestBlameDiffMetricsUtils(unittest.TestCase):
    """Test functions to create blame diff dependent databases."""

    @classmethod
    def setUp(cls) -> None:

        with NamedTemporaryFile('w') as yaml_file:
            yaml_file.write(YAML_CASE_STUDY)
            yaml_file.seek(0)
            cls.case_study = load_case_study_from_file(Path(yaml_file.name))

        cls.br_paths_list = [
            get_path_to_test_inputs() / Path(
                "results/xz/BR-xz-xz-2f0bc9cd40"
                "_9e238675-ee7c-4325-8e9f-8ccf6fd3f05c_success.yaml"
            ),
            get_path_to_test_inputs() / Path(
                "results/xz/BR-xz-xz-c5c7ceb08a"
                "_77a6c5bc-e5c7-4532-8814-70dbcc6b5dda_success.yaml"
            ),
            get_path_to_test_inputs() / Path(
                "results/xz/BR-xz-xz-ef364d3abc"
                "_feeeecb2-1826-49e5-a188-d4d883f06d00_success.yaml"
            )
        ]

    def test_id_from_paths(self) -> None:
        """Test if the commit hashes of two result files are extracted and
        concatenated correctly to a combined hash."""

        combined_c_hash = id_from_paths(
            (self.br_paths_list[0], self.br_paths_list[1])
        )
        self.assertTrue("2f0bc9cd40_c5c7ceb08a", combined_c_hash)

    def test_timestamp_from_paths(self) -> None:
        """Test if the timestamp of two result files are extracted and
        concatenated correctly to a combined timestamp."""
        combined_timestamp1 = timestamp_from_paths(
            (self.br_paths_list[0], self.br_paths_list[1])
        )
        combined_timestamp2 = timestamp_from_paths(
            (self.br_paths_list[1], self.br_paths_list[2])
        )
        self.assertTrue(
            "1612953595877546924_1612953595881546917", combined_timestamp1
        )
        self.assertTrue(
            "1612953595881546917_1612953595881546917", combined_timestamp2
        )

    def test_compare_timestamps(self) -> None:
        """Test if newer timestamp is correctly determined."""
        comp1 = compare_timestamps(
            "1612953595881546917_2612953595877546924",
            "3612953595881546917_1612953595877546924"
        )
        comp2 = compare_timestamps(
            "1612953595881546917_1712953595877546924",
            "3612953595881546917_1612953595877546924"
        )
        comp3 = compare_timestamps(
            "1612953595881546917_1712953595877546924",
            "2612953595881546917_2712953595877546924"
        )
        self.assertTrue(comp1)
        self.assertTrue(comp2)
        self.assertFalse(comp3)

    @mock.patch(
        "varats.data.databases.blame_diff_metrics_database"
        ".get_failed_revisions_files"
    )
    @mock.patch(
        "varats.data.databases.blame_diff_metrics_database"
        ".get_processed_revisions_files"
    )
    def test_build_report_files_tuple(
        self, mock_processed_revisions, mock_failed_revisions
    ) -> None:
        """Test if the mappings from commit hash to successful and failed report
        files are correctly returned as tuple."""
        mock_processed_revisions.return_value = self.br_paths_list
        mock_failed_revisions.return_value = self.br_paths_list[0:2]
        report_files_tuple = build_report_files_tuple("mocked", None)

        successful_revisions = {
            '2f0bc9cd40': self.br_paths_list[0],
            'c5c7ceb08a': self.br_paths_list[1],
            'ef364d3abc': self.br_paths_list[2]
        }
        failed_revisions = {
            '2f0bc9cd40': self.br_paths_list[0],
            'c5c7ceb08a': self.br_paths_list[1]
        }

        self.assertTrue(
            report_files_tuple, (successful_revisions, failed_revisions)
        )
