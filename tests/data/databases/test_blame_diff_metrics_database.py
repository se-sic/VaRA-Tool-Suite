"""Test blame diff based commit-data metrics."""
import typing as tp
import unittest
import unittest.mock as mock
from collections import defaultdict
from pathlib import Path
from tempfile import NamedTemporaryFile

from tests.paper.test_case_study import YAML_CASE_STUDY
from varats.data.databases.blame_diff_metrics_database import (
    id_from_paths,
    timestamp_from_paths,
    compare_timestamps,
    build_report_files_tuple,
    build_report_pairs_tuple,
    get_predecessor_report_file,
    get_successor_report_file,
)
from varats.data.reports.blame_report import BlameReport
from varats.mapping.commit_map import get_commit_map
from varats.paper.case_study import load_case_study_from_file
from varats.projects.discover_projects import initialize_projects
from varats.revision.revisions import get_processed_revisions
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
            ),
            get_path_to_test_inputs() / Path(
                "results/TwoLibsOneProjectInteractionDiscreteLibsSingleProject/"
                "BR-TwoLibsOneProjectInteractionDiscreteLibsSingleProject-"
                "elementalist-5e8fe1616d_11ca651c-2d41-42bd-aa4e-8c37ba67b75f"
                "_success.yaml"
            ),
            get_path_to_test_inputs() / Path(
                "results/TwoLibsOneProjectInteractionDiscreteLibsSingleProject/"
                "BR-TwoLibsOneProjectInteractionDiscreteLibsSingleProject-"
                "elementalist-e64923e69e_0b22c10c-4adb-4885-b3d2-416749b53aa8"
                "_success.yaml"
            )
        ]

    def test_id_from_paths(self) -> None:
        """Test if the commit hashes of two result files are extracted and
        concatenated correctly to a combined hash."""

        combined_c_hash = id_from_paths(
            (self.br_paths_list[0], self.br_paths_list[1])
        )
        self.assertEqual("2f0bc9cd40_c5c7ceb08a", combined_c_hash)

    def test_timestamp_from_paths(self) -> None:
        """Test if the timestamp of two result files are extracted and
        concatenated correctly to a combined timestamp."""
        combined_timestamp1 = timestamp_from_paths(
            (self.br_paths_list[0], self.br_paths_list[1])
        )
        combined_timestamp2 = timestamp_from_paths(
            (self.br_paths_list[1], self.br_paths_list[2])
        )
        self.assertEqual(
            "1612953595877546924_1612953595881546917", combined_timestamp1
        )
        self.assertEqual(
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

    @mock.patch("varats.revision.revisions.__get_result_files_dict")
    def test_build_report_files_tuple(self, mock_result_files_dict) -> None:
        """Test if the mappings from commit hash to successful and failed report
        files are correctly returned as tuple."""

        mock_result_files = defaultdict(list)
        mock_result_files["5e8fe1616d"] = [self.br_paths_list[3]]
        mock_result_files["e64923e69e"] = [self.br_paths_list[4]]

        mock_result_files_dict.return_value = mock_result_files

        case_study = load_case_study_from_file(
            get_path_to_test_inputs() / Path(
                "paper_configs/test_blame_diff_metrics_database/"
                "TwoLibsOneProjectInteractionDiscreteLibsSingleProject_0."
                "case_study"
            )
        )
        report_files_tuple = build_report_files_tuple(
            case_study.project_name, case_study
        )

        successful_revisions: tp.Dict[str, tp.List[Path]] = {
            '5e8fe1616d': self.br_paths_list[3],
            'e64923e69e': self.br_paths_list[4],
        }
        failed_revisions: tp.Dict[str, tp.List[Path]] = {}

        self.assertEqual(
            report_files_tuple, (successful_revisions, failed_revisions)
        )

    @mock.patch("varats.revision.revisions.__get_result_files_dict")
    def test_build_report_pairs_tuple(self, mock_result_files_dict) -> None:
        """Test if the tuple of ReportPairTupleList tuples is correctly
        built."""

        mock_result_files = defaultdict(list)
        mock_result_files["5e8fe1616d"] = [self.br_paths_list[3]]
        mock_result_files["e64923e69e"] = [self.br_paths_list[4]]

        mock_result_files_dict.return_value = mock_result_files

        initialize_projects()
        commit_map = get_commit_map(
            "TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
        )
        case_study = load_case_study_from_file(
            get_path_to_test_inputs() / Path(
                "paper_configs/test_blame_diff_metrics_database/"
                "TwoLibsOneProjectInteractionDiscreteLibsSingleProject_0."
                "case_study"
            )
        )

        report_pairs_tuple = build_report_pairs_tuple(
            case_study.project_name, commit_map, case_study
        )

        mock_report_pairs_list: tp.List[tp.Tuple[Path, Path]] = [
            (self.br_paths_list[3], self.br_paths_list[4])
        ]
        mock_failed_report_pairs_list: tp.List[tp.Tuple[Path, Path]] = []

        self.assertEqual(
            report_pairs_tuple,
            (mock_report_pairs_list, mock_failed_report_pairs_list)
        )

    @mock.patch("varats.revision.revisions.__get_result_files_dict")
    def test_get_predecessor_report_file(self, mock_result_files_dict) -> None:
        """Test if the correct preceding report file of a report is found."""
        mock_result_files = defaultdict(list)
        mock_result_files["5e8fe1616d"] = [self.br_paths_list[3]]
        mock_result_files["e64923e69e"] = [self.br_paths_list[4]]

        mock_result_files_dict.return_value = mock_result_files

        initialize_projects()
        commit_map = get_commit_map(
            "TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
        )
        case_study = load_case_study_from_file(
            get_path_to_test_inputs() / Path(
                "paper_configs/test_blame_diff_metrics_database/"
                "TwoLibsOneProjectInteractionDiscreteLibsSingleProject_0."
                "case_study"
            )
        )
        report_files, _ = build_report_files_tuple(
            case_study.project_name, case_study
        )
        sampled_revs = get_processed_revisions(
            case_study.project_name, BlameReport
        )
        short_time_id_cache: tp.Dict[str, int] = {
            rev: commit_map.short_time_id(rev) for rev in sampled_revs
        }

        predecessor_of_e6 = get_predecessor_report_file(
            "e64923e69e", commit_map, short_time_id_cache, report_files,
            sampled_revs
        )
        predecessor_of_5e = get_predecessor_report_file(
            "5e8fe1616d", commit_map, short_time_id_cache, report_files,
            sampled_revs
        )

        self.assertEqual(predecessor_of_e6, None)
        self.assertEqual(predecessor_of_5e, self.br_paths_list[4])

    @mock.patch("varats.revision.revisions.__get_result_files_dict")
    def test_get_successor_report_file(self, mock_result_files_dict) -> None:
        """Test if the correct succeeding report file of a report is found."""

        mock_result_files = defaultdict(list)
        mock_result_files["5e8fe1616d"] = [self.br_paths_list[3]]
        mock_result_files["e64923e69e"] = [self.br_paths_list[4]]

        mock_result_files_dict.return_value = mock_result_files

        initialize_projects()
        commit_map = get_commit_map(
            "TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
        )
        case_study = load_case_study_from_file(
            get_path_to_test_inputs() / Path(
                "paper_configs/test_blame_diff_metrics_database/"
                "TwoLibsOneProjectInteractionDiscreteLibsSingleProject_0."
                "case_study"
            )
        )
        report_files, _ = build_report_files_tuple(
            case_study.project_name, case_study
        )
        sampled_revs = get_processed_revisions(
            case_study.project_name, BlameReport
        )
        short_time_id_cache: tp.Dict[str, int] = {
            rev: commit_map.short_time_id(rev) for rev in sampled_revs
        }

        successor_of_e6 = get_successor_report_file(
            "e64923e69e", commit_map, short_time_id_cache, report_files,
            sampled_revs
        )
        successor_of_5e = get_successor_report_file(
            "5e8fe1616d", commit_map, short_time_id_cache, report_files,
            sampled_revs
        )

        self.assertEqual(successor_of_e6, self.br_paths_list[3])
        self.assertEqual(successor_of_5e, None)
