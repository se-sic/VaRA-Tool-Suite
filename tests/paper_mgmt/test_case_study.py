"""Test case study."""
import os
import random
import unittest
from datetime import datetime
from pathlib import Path

import varats.paper_mgmt.case_study as MCS
from tests.helper_utils import run_in_test_environment, UnitTestFixtures
from varats.data.reports.commit_report import CommitReport as CR
from varats.experiments.base.just_compile import JustCompileReport
from varats.experiments.vara.commit_report_experiment import (
    CommitReportExperiment,
)
from varats.mapping.commit_map import get_commit_map
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_paper_config, load_paper_config
from varats.plot.plots import PlotConfig
from varats.plots.case_study_overview import CaseStudyOverviewPlot
from varats.project.project_util import get_local_project_git_path
from varats.projects.discover_projects import initialize_projects
from varats.report.report import FileStatusExtension, ReportFilename
from varats.utils.git_util import FullCommitHash, ShortCommitHash
from varats.utils.settings import vara_cfg


class TestCaseStudyRevisionLookupFunctions(unittest.TestCase):
    """Test if revision look up functions find the correct revisions."""

    @classmethod
    def setUpClass(cls) -> None:
        initialize_projects()

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_newest_processed_revision(self) -> None:
        """Check whether the newest processed revision is correctly
        identified."""
        vara_cfg()['paper_config']['current_config'] = "test_revision_lookup"
        load_paper_config()

        newest_processed = MCS.newest_processed_revision_for_case_study(
            get_paper_config().get_case_studies('brotli')[0],
            CommitReportExperiment
        )

        self.assertEqual(
            FullCommitHash('21ac39f7c8ca61c855be0bc38900abe7b5a0f67f'),
            newest_processed
        )

    @run_in_test_environment(UnitTestFixtures.PAPER_CONFIGS)
    def test_newest_processed_revision_no_results(self) -> None:
        """Check None is returned when no results are available."""
        vara_cfg()['paper_config']['current_config'] = "test_revision_lookup"
        load_paper_config()

        newest_processed = MCS.newest_processed_revision_for_case_study(
            get_paper_config().get_case_studies('brotli')[0],
            CommitReportExperiment
        )

        self.assertIsNone(newest_processed)

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_get_failed_revisions(self) -> None:
        """Check if we can correctly find all failed revisions of a case
        study."""
        vara_cfg()['paper_config']['current_config'] = "test_revision_lookup"
        load_paper_config()

        failed_revs = MCS.failed_revisions_for_case_study(
            get_paper_config().get_case_studies('brotli')[0],
            CommitReportExperiment
        )

        self.assertEqual(len(failed_revs), 1)
        self.assertTrue(
            FullCommitHash('aaa4424d9bdeb10f8af5cb4599a0fc2bbaac5553') in
            failed_revs
        )

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_get_processed_revisions(self) -> None:
        """Check if we can correctly find all processed revisions of a case
        study."""
        vara_cfg()['paper_config']['current_config'] = "test_revision_lookup"
        load_paper_config()

        process_revs = MCS.processed_revisions_for_case_study(
            get_paper_config().get_case_studies('brotli')[0],
            CommitReportExperiment
        )

        self.assertEqual(len(process_revs), 1)
        self.assertTrue(
            FullCommitHash('21ac39f7c8ca61c855be0bc38900abe7b5a0f67f') in
            process_revs
        )

    @run_in_test_environment(UnitTestFixtures.PAPER_CONFIGS)
    def test_get_revisions_status_for_case_study_to_high_stage(self) -> None:
        """Check if we correctly handle lookups where the stage selected is
        larger than the biggest one in the case study."""
        vara_cfg()['paper_config']['current_config'] = "test_revision_lookup"
        load_paper_config()

        self.assertListEqual(
            MCS.get_revisions_status_for_case_study(
                get_paper_config().get_case_studies('brotli')[0],
                CommitReportExperiment,
                stage_num=9001
            ), []
        )

    @run_in_test_environment(UnitTestFixtures.PAPER_CONFIGS)
    def test_get_revision_not_in_case_study(self) -> None:
        """Check if we correctly handle the lookup of a revision that is not in
        the case study."""
        vara_cfg()['paper_config']['current_config'] = "test_revision_lookup"
        load_paper_config()

        self.assertRaises(
            ValueError, MCS.get_revision_status_for_case_study,
            get_paper_config().get_case_studies('brotli')[0],
            ShortCommitHash('0000000000'), CommitReportExperiment, CR
        )

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_get_revisions_in_case_study(self) -> None:
        """Check if we correctly handle the lookup of a revision that is in a
        case study."""
        vara_cfg()['paper_config']['current_config'] = "test_revision_lookup"
        load_paper_config()

        self.assertEqual(
            MCS.get_revision_status_for_case_study(
                get_paper_config().get_case_studies('brotli')[0],
                ShortCommitHash('21ac39f7c8'), CommitReportExperiment, CR
            ), FileStatusExtension.SUCCESS
        )

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_get_newest_result_files_for_case_study(self) -> None:
        """Check that when we have two files, the newes one get's selected."""
        vara_cfg()['paper_config']['current_config'] = "test_revision_lookup"
        load_paper_config()

        good_file = ReportFilename(
            'CRE-CR-brotli-brotli-21ac39f7c8_'
            '34d4d1b5-7212-4244-9adc-b19bff599142_success.yaml'
        )

        now = datetime.now().timestamp()
        file_path = Path(
            str(vara_cfg()['result_dir'])
        ) / 'brotli' / good_file.filename
        os.utime(file_path, (now, now))

        newest_res_files = MCS.get_newest_result_files_for_case_study(
            get_paper_config().get_case_studies('brotli')[0],
            Path(vara_cfg()['result_dir'].value), CR
        )

        # remove unnecessary files
        filtered_newest_res_files = list(
            filter(
                lambda res_file: res_file.commit_hash == good_file.commit_hash,
                map(
                    lambda res_file: ReportFilename(res_file), newest_res_files
                )
            )
        )

        self.assertTrue(filtered_newest_res_files[0].uuid.endswith('42'))

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_get_newest_result_files_for_case_study_fail(self) -> None:
        """Check that when we have two files, the newes one get's selected."""
        vara_cfg()['paper_config']['current_config'] = "test_revision_lookup"
        load_paper_config()

        bad_file = ReportFilename(
            'CRE-CR-brotli-brotli-21ac39f7c8_'
            '34d4d1b5-7212-4244-9adc-b19bff599cf1_success.yaml'
        )

        now = datetime.now().timestamp()
        file_path = Path(
            str(vara_cfg()['result_dir'])
        ) / 'brotli' / bad_file.filename
        os.utime(file_path, (now, now))

        newest_res_files = MCS.get_newest_result_files_for_case_study(
            get_paper_config().get_case_studies('brotli')[0],
            Path(vara_cfg()['result_dir'].value), CR
        )

        # remove unnecessary files
        filtered_newest_res_files = list(
            filter(
                lambda res_file: res_file.commit_hash == bad_file.commit_hash,
                map(
                    lambda res_file: ReportFilename(res_file), newest_res_files
                )
            )
        )

        self.assertFalse(filtered_newest_res_files[0].uuid.endswith('42'))

    @run_in_test_environment(UnitTestFixtures.PAPER_CONFIGS)
    def test_get_newest_result_files_for_case_study_with_empty_res_dir(
        self
    ) -> None:
        """Check that we correctly handle the edge case where no result dir
        exists."""
        vara_cfg()['paper_config']['current_config'] = "test_revision_lookup"
        load_paper_config()

        self.assertListEqual(
            MCS.get_newest_result_files_for_case_study(
                get_paper_config().get_case_studies('brotli')[0],
                Path(vara_cfg()['result_dir'].value), CR
            ), []
        )

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_get_newest_result_files_for_case_study_with_config(self) -> None:
        """Check that when we have two files, the newes one get's selected."""
        vara_cfg()['paper_config']['current_config'] = "test_config_ids"
        load_paper_config()

        config_0_file = ReportFilename(
            "BBBase-CR-SynthSAContextSensitivity-ContextSense-06eac0edb6/"
            "b24ee2c1-fc85-47ba-abbd-90c98e88a37c_config-0_success.zip"
        )
        config_1_file = ReportFilename(
            "BBBase-CR-SynthSAContextSensitivity-ContextSense-06eac0edb6/"
            "8380144f-9a25-44c6-8ce0-08d0a29c677b_config-1_success.zip"
        )

        now = datetime.now().timestamp()
        file_path_0 = Path(
            str(vara_cfg()['result_dir'])
        ) / 'SynthSAContextSensitivity' / config_0_file.filename
        os.utime(file_path_0, (now, now))

        file_path_1 = Path(
            str(vara_cfg()['result_dir'])
        ) / 'SynthSAContextSensitivity' / config_1_file.filename
        os.utime(file_path_1, (now, now))

        newest_res_files = MCS.get_newest_result_files_for_case_study(
            get_paper_config().get_case_studies('SynthSAContextSensitivity')[0],
            Path(vara_cfg()['result_dir'].value), CR
        )

        newest_res_files.sort(reverse=True)
        newest_res_filenames = [ReportFilename(x) for x in newest_res_files]

        self.assertEqual(newest_res_filenames[0].config_id, 0)
        self.assertEqual(newest_res_filenames[1].config_id, 1)
        self.assertEqual(len(newest_res_filenames), 2)

    def test_get_case_study_file_name_filter_empty(self) -> None:
        """Check that we correctly handle  case study filter generation even if
        no case study was provided."""

        cs_filter = MCS.get_case_study_file_name_filter(None)

        self.assertFalse(cs_filter('foo/bar'))


class TestCaseStudyExtenders(unittest.TestCase):

    def test_extend_with_revs_per_year(self) -> None:
        initialize_projects()
        random.seed(42)

        cs = CaseStudy("xz", 0)
        git_path = get_local_project_git_path("xz")
        cmap = get_commit_map(
            "xz", end="c5c7ceb08a011b97d261798033e2c39613a69eb7"
        )

        MCS.extend_with_revs_per_year(cs, cmap, 0, True, str(git_path), 2, True)
        self.assertEqual(cs.num_stages, 17)
        self.assertEqual(len(cs.revisions), 31)
        self.assertEqual(
            cs.get_stage_by_name('2022').revisions[0],
            FullCommitHash("8fd225a2c149f30aeac377e68eb5abf6b28300ad")
        )
        self.assertEqual(
            cs.revisions[-1],
            FullCommitHash("ec490da5228263b25bf786bb23d1008468f55b30")
        )

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_extend_with_smooth_revs(self) -> None:
        initialize_projects()
        vara_cfg()['paper_config']['current_config'] = "test_revision_lookup"
        load_paper_config()

        cs = get_paper_config().get_case_studies("brotli")[0]
        cmap = get_commit_map(
            "brotli", end="aaa4424d9bdeb10f8af5cb4599a0fc2bbaac5553"
        )

        MCS.extend_with_smooth_revs(
            cs, cmap, 0, True,
            CaseStudyOverviewPlot(
                PlotConfig.from_kwargs(False),
                case_study=cs,
                experiment_type=JustCompileReport
            ), 1
        )
        self.assertEqual(cs.num_stages, 2)
        self.assertEqual(len(cs.revisions), 7)
        self.assertIn(
            FullCommitHash("5814438791fb2d4394b46e5682a96b68cd092803"),
            cs.stages[1].revisions
        )
        self.assertIn(
            FullCommitHash("510131d1db47f91602f45b9a8d7b1ee54d12a629"),
            cs.stages[1].revisions
        )
