"""Test blame diff based commit-data metrics."""
import unittest
import unittest.mock as mock
from pathlib import Path

from varats.data.databases.blame_diff_metrics_database import (
    id_from_paths,
    timestamp_from_paths,
    compare_timestamps,
)


class TestBlameDiffMetricsUtils(unittest.TestCase):
    """Test functions to create blame diff dependent databases."""

    @classmethod
    def setUp(cls) -> None:
        cls.br_paths_list = [
            Path(__file__).parents[2] / Path(
                "TEST_INPUTS/results/xz/BR-xz-xz-2f0bc9cd40"
                "_9e238675-ee7c-4325-8e9f-8ccf6fd3f05c_success.yaml"
            ),
            Path(__file__).parents[2] / Path(
                "TEST_INPUTS/results/xz/BR-xz-xz-c5c7ceb08a"
                "_77a6c5bc-e5c7-4532-8814-70dbcc6b5dda_success.yaml"
            ),
            Path(__file__).parents[2] / Path(
                "TEST_INPUTS/results/xz/BR-xz-xz-ef364d3abc"
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
