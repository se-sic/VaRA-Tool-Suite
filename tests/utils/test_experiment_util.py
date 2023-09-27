"""Test VaRA Experiment utilities."""
import os
import shutil
import tempfile
import typing as tp
import unittest
import unittest.mock as mock
from pathlib import Path

import benchbuild.utils.actions as actions
import benchbuild.utils.settings as s
from benchbuild.project import Project
from benchbuild.source.base import Revision, Variant

import varats.experiment.experiment_util as EU
from tests.helper_utils import (
    run_in_test_environment,
    BBTestSource,
    UnitTestFixtures,
)
from varats.data.reports.commit_report import CommitReport as CR
from varats.experiments.base.just_compile import JustCompileReport
from varats.paper.paper_config import load_paper_config
from varats.project.project_util import BinaryType, ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.projects.c_projects.xz import Xz
from varats.projects.perf_tests.feature_perf_cs_collection import (
    SynthIPTemplate,
)
from varats.report.gnu_time_report import TimeReport
from varats.report.report import FileStatusExtension, ReportSpecification
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import vara_cfg, bb_cfg


class MockExperiment(EU.VersionExperiment, shorthand="mock"):
    """Small MockExperiment to be used as a replacement for actual
    experiments."""

    NAME = "CommitReportExperiment"
    REPORT_SPEC = ReportSpecification(CR)

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        return []


class MockExperimentMultiReport(EU.VersionExperiment, shorthand="mock"):
    """Small MockExperiment to be used as a replacement for actual experiments
    that "produces" multiple reports."""

    NAME = "CommitReportExperiment"
    REPORT_SPEC = ReportSpecification(CR, TimeReport)

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        return []


class BBTestProject(Project):
    """Test project for version sampling tests."""
    NAME = "test_empty"

    DOMAIN = "debug"
    GROUP = "debug"
    SOURCE = [
        BBTestSource(
            test_versions=[
                'rev1000000', 'rev2000000', 'rev3000000', 'rev4000000',
                'rev5000000'
            ],
            local="/dev/null",
            remote="/dev/null"
        )
    ]

    def build(self):
        pass

    def configure(self):
        pass

    def download(self, version=None):
        pass

    def compile(self):
        pass

    def run_tests(self) -> None:
        pass


class TestResultFolderAccess(unittest.TestCase):
    """Test result folder access."""

    @run_in_test_environment()
    def test_result_folder_creation(self):
        """Checks if we get the correct result folder back."""
        test_tmp_folder = str(os.getcwd())

        bb_cfg()["varats"]["outfile"] = test_tmp_folder + "/results"

        result_folder = EU.get_varats_result_folder(BBTestProject())
        self.assertEqual(
            test_tmp_folder + "/results/" + BBTestProject.NAME,
            str(result_folder)
        )
        self.assertTrue(result_folder.exists())


class TestVersionExperiment(unittest.TestCase):
    """Test VersionExperiments sampling behaviour."""

    tmp_path: tempfile.TemporaryDirectory
    vers_expr: MockExperiment

    @classmethod
    def setUpClass(cls):
        """Load and parse function infos from yaml file."""
        cls.vers_expr = MockExperiment()
        cls.rev_list = [
            'rev1000000', 'rev2000000', 'rev3000000', 'rev4000000', 'rev5000000'
        ]

    def setUp(self):
        """Set config to initial values."""
        self.rev_list = [
            'rev1000000', 'rev2000000', 'rev3000000', 'rev4000000', 'rev5000000'
        ]

    @staticmethod
    def prepare_vara_config(vara_cfg: s.Configuration) -> None:
        vara_cfg["experiment"]["sample_limit"] = None
        vara_cfg["experiment"]["random_order"] = False
        vara_cfg["experiment"]["file_status_whitelist"] = []
        vara_cfg["experiment"]["file_status_blacklist"] = []

    @staticmethod
    def generate_get_tagged_revisions_output(
    ) -> dict[ShortCommitHash, dict[tp.Optional[int], FileStatusExtension]]:
        """Generate get_tagged_revisions output for mocking."""
        return {
            ShortCommitHash('rev1000000'): {
                None: FileStatusExtension.SUCCESS
            },
            ShortCommitHash('rev2000000'): {
                None: FileStatusExtension.BLOCKED
            },
            ShortCommitHash('rev3000000'): {
                None: FileStatusExtension.COMPILE_ERROR
            },
            ShortCommitHash('rev4000000'): {
                None: FileStatusExtension.FAILED
            },
            ShortCommitHash('rev5000000'): {
                None: FileStatusExtension.MISSING
            }
        }

    @run_in_test_environment()
    def test_sample_limit(self):
        """Test if base_hash is loaded correctly."""
        self.prepare_vara_config(vara_cfg())
        self.assertEqual(vara_cfg()["experiment"]["sample_limit"].value, None)
        self.assertEqual(
            # pylint: disable=protected-access
            self.vers_expr._sample_num_versions(self.rev_list),
            self.rev_list
        )

        vara_cfg()["experiment"]["sample_limit"] = 3
        self.assertEqual(
            len(self.vers_expr._sample_num_versions(self.rev_list)), 3
        )

    @run_in_test_environment()
    def test_without_versions(self):
        """Test if we get the correct revision if no VaRA modifications are
        enabled."""
        bb_cfg()["versions"]["full"] = False
        sample_gen = self.vers_expr.sample(BBTestProject)
        self.assertEqual(sample_gen[0].primary.version, "rev1000000")
        self.assertEqual(len(sample_gen), 1)

    @run_in_test_environment()
    @mock.patch('varats.experiment.experiment_util.revs.get_tagged_revisions')
    def test_only_whitelisting_one(self, mock_get_tagged_revisions):
        """Test if we can whitelist file status."""
        self.prepare_vara_config(vara_cfg())
        bb_cfg()["versions"]["full"] = True
        # Revision not in set
        mock_get_tagged_revisions.return_value = \
            self.generate_get_tagged_revisions_output()

        vara_cfg()["experiment"]["file_status_whitelist"] = ['success']

        sample_gen = self.vers_expr.sample(BBTestProject)

        self.assertEqual(sample_gen[0].primary.version, "rev1000000")
        self.assertEqual(len(sample_gen), 1)
        mock_get_tagged_revisions.assert_called()

    @run_in_test_environment()
    @mock.patch('varats.experiment.experiment_util.revs.get_tagged_revisions')
    def test_only_whitelisting_many(self, mock_get_tagged_revisions):
        """Test if we can whitelist file status."""
        self.prepare_vara_config(vara_cfg())
        bb_cfg()["versions"]["full"] = True
        # Revision not in set
        mock_get_tagged_revisions.return_value = \
            self.generate_get_tagged_revisions_output()

        vara_cfg()["experiment"]["file_status_whitelist"] = [
            'success', 'Failed', 'Missing'
        ]

        sample_gen = self.vers_expr.sample(BBTestProject)

        self.assertEqual(sample_gen[0].primary.version, "rev1000000")
        self.assertEqual(sample_gen[1].primary.version, "rev4000000")
        self.assertEqual(sample_gen[2].primary.version, "rev5000000")
        self.assertEqual(len(sample_gen), 3)
        mock_get_tagged_revisions.assert_called()

    @run_in_test_environment()
    @mock.patch('varats.experiment.experiment_util.revs.get_tagged_revisions')
    def test_only_blacklisting_one(self, mock_get_tagged_revisions):
        """Test if we can blacklist file status."""
        self.prepare_vara_config(vara_cfg())
        bb_cfg()["versions"]["full"] = True
        # Revision not in set
        mock_get_tagged_revisions.return_value = \
            self.generate_get_tagged_revisions_output()

        vara_cfg()["experiment"]["file_status_blacklist"] = ['success']

        sample_gen = self.vers_expr.sample(BBTestProject)
        self.assertEqual(sample_gen[0].primary.version, "rev2000000")
        self.assertEqual(sample_gen[1].primary.version, "rev3000000")
        self.assertEqual(sample_gen[2].primary.version, "rev4000000")
        self.assertEqual(sample_gen[3].primary.version, "rev5000000")
        self.assertEqual(len(sample_gen), 4)
        mock_get_tagged_revisions.assert_called()

    @run_in_test_environment()
    @mock.patch('varats.experiment.experiment_util.revs.get_tagged_revisions')
    def test_only_blacklisting_many(self, mock_get_tagged_revisions):
        """Test if we can blacklist file status."""
        self.prepare_vara_config(vara_cfg())
        bb_cfg()["versions"]["full"] = True
        # Revision not in set
        mock_get_tagged_revisions.return_value = \
            self.generate_get_tagged_revisions_output()

        vara_cfg()["experiment"]["file_status_blacklist"] = [
            'success', 'Failed', 'Blocked'
        ]

        sample_gen = self.vers_expr.sample(BBTestProject)

        self.assertEqual(sample_gen[0].primary.version, "rev3000000")
        self.assertEqual(sample_gen[1].primary.version, "rev5000000")
        self.assertEqual(len(sample_gen), 2)
        mock_get_tagged_revisions.assert_called()

    @run_in_test_environment()
    @mock.patch('varats.experiment.experiment_util.revs.get_tagged_revisions')
    def test_white_overwrite_blacklisting(self, mock_get_tagged_revisions):
        """Test if whitelist overwrites blacklist."""
        self.prepare_vara_config(vara_cfg())
        bb_cfg()["versions"]["full"] = True
        # Revision not in set
        mock_get_tagged_revisions.return_value = \
            self.generate_get_tagged_revisions_output()

        vara_cfg()["experiment"]["file_status_blacklist"] = ['Failed']
        vara_cfg()["experiment"]["file_status_whitelist"] = ['Failed']

        sample_gen = self.vers_expr.sample(BBTestProject)

        self.assertEqual(sample_gen[0].primary.version, "rev4000000")
        self.assertEqual(len(sample_gen), 1)
        mock_get_tagged_revisions.assert_called()

    def test_file_belongs_to_experiment(self) -> None:
        self.assertTrue(
            JustCompileReport.
            file_belongs_to_experiment("JC-EMPTY-xz-xz-__success.txt")
        )
        self.assertFalse(
            JustCompileReport.
            file_belongs_to_experiment("BR-EMPTY-xz-xz-__success.txt")
        )
        self.assertFalse(JustCompileReport.file_belongs_to_experiment("foo"))

    @run_in_test_environment()
    def test_create_success_result_filepath(self):
        """Checks if we correctly create new success result files."""
        new_res_file = EU.create_new_success_result_filepath(
            self.vers_expr.get_handle(), CR, tp.cast(VProject, BBTestProject()),
            ProjectBinaryWrapper("foo", Path("bar/foo"), BinaryType.EXECUTABLE)
        )

        self.assertTrue(new_res_file.base_path.exists())

        report_filename = new_res_file.report_filename
        self.assertEqual(
            report_filename.file_status, FileStatusExtension.SUCCESS
        )
        self.assertEqual(report_filename.config_id, None)

    @run_in_test_environment()
    def test_create_failed_result_filepath(self):
        """Checks if we correctly create new failed result files."""
        new_res_file = EU.create_new_failed_result_filepath(
            self.vers_expr.get_handle(), CR, tp.cast(VProject, BBTestProject()),
            ProjectBinaryWrapper("foo", Path("bar/foo"), BinaryType.EXECUTABLE)
        )

        self.assertTrue(new_res_file.base_path.exists())

        report_filename = new_res_file.report_filename
        self.assertEqual(
            report_filename.file_status, FileStatusExtension.FAILED
        )
        self.assertEqual(report_filename.config_id, None)

    @run_in_test_environment()
    def test_create_success_result_filepath_config(self):
        """Checks if we correctly create new success config-specific result
        files."""
        new_res_file = EU.create_new_success_result_filepath(
            self.vers_expr.get_handle(), CR, tp.cast(VProject, BBTestProject()),
            ProjectBinaryWrapper("foo", Path("bar/foo"), BinaryType.EXECUTABLE),
            42
        )

        self.assertTrue(new_res_file.base_path.exists())

        report_filename = new_res_file.report_filename
        self.assertEqual(
            report_filename.file_status, FileStatusExtension.SUCCESS
        )
        self.assertEqual(report_filename.config_id, 42)
        self.assertTrue((
            new_res_file.base_path / Path("mock-CR-test_empty-foo-rev1000000")
        ).exists())
        self.assertTrue((
            new_res_file.base_path / Path("mock-CR-test_empty-foo-rev1000000")
        ).is_dir())

    @run_in_test_environment()
    def test_create_success_result_filepath_config_with_id_zero(self):
        """Checks if we correctly create new success config-specific result
        files for config id zero."""
        new_res_file = EU.create_new_success_result_filepath(
            self.vers_expr.get_handle(), CR, tp.cast(VProject, BBTestProject()),
            ProjectBinaryWrapper("foo", Path("bar/foo"), BinaryType.EXECUTABLE),
            0
        )

        self.assertTrue(new_res_file.base_path.exists())

        report_filename = new_res_file.report_filename
        self.assertEqual(
            report_filename.file_status, FileStatusExtension.SUCCESS
        )
        self.assertEqual(report_filename.config_id, 0)
        self.assertTrue((
            new_res_file.base_path / Path("mock-CR-test_empty-foo-rev1000000")
        ).exists())
        self.assertTrue((
            new_res_file.base_path / Path("mock-CR-test_empty-foo-rev1000000")
        ).is_dir())


class TestZippedReportFolder(unittest.TestCase):
    """Test ZippedReportFolder creation."""

    @run_in_test_environment()
    def test_zipped_result_folder_creation(self):
        """Checks if a zipped result folder is automatically created."""
        test_tmp_folder = Path(os.getcwd())

        test_zip = test_tmp_folder / 'FooBar.zip'

        with EU.ZippedReportFolder(test_zip) as output_folder:
            with open(Path(output_folder) / 'foo.txt', 'w') as output_file:
                output_file.write('content')

        self.assertTrue(test_zip.exists())

        with tempfile.TemporaryDirectory() as tmp_result_dir:
            shutil.unpack_archive(test_zip, extract_dir=Path(tmp_result_dir))

            should_be_generated_file = Path(tmp_result_dir) / 'foo.txt'
            self.assertTrue(should_be_generated_file.exists())
            with open(should_be_generated_file, 'r') as foo_file:
                self.assertEqual(foo_file.readline(), 'content')


class TestConfigID(unittest.TestCase):

    def test_get_current_config_id_no_config(self) -> None:
        revision = Revision(Xz, Variant(Xz.SOURCE[0], "c5c7ceb08a"))
        project = Xz(revision=revision)
        self.assertEqual(EU.get_current_config_id(project), None)

    def test_get_current_config_id(self) -> None:
        revision = Revision(
            Xz, Variant(Xz.SOURCE[0], "c5c7ceb08a"),
            Variant(Xz.SOURCE[1], "42")
        )
        project = Xz(revision=revision)
        self.assertEqual(EU.get_current_config_id(project), 42)

    @run_in_test_environment(UnitTestFixtures.PAPER_CONFIGS)
    def test_get_extra_config_options(self) -> None:
        vara_cfg()['paper_config']['current_config'] = "test_config_ids"
        load_paper_config()

        revision = Revision(
            Xz, Variant(Xz.SOURCE[0], "c5c7ceb08a"), Variant(Xz.SOURCE[1], "1")
        )
        project = Xz(revision=revision)
        self.assertEqual(EU.get_extra_config_options(project), ["--foo"])

    @run_in_test_environment(UnitTestFixtures.PAPER_CONFIGS)
    def test_get_config_patches(self) -> None:
        vara_cfg()['paper_config']['current_config'] = "test_config_ids"
        load_paper_config()

        revision = Revision(
            SynthIPTemplate, Variant(SynthIPTemplate.SOURCE[0], "7930350628"),
            Variant(SynthIPTemplate.SOURCE[1], "4")
        )
        project = SynthIPTemplate(revision=revision)
        patches = EU.get_config_patches(project)
        self.assertEqual(len(patches), 1)
        self.assertEqual(
            list(patches)[0].feature_tags,
            ["Compress", "fastmode", "smallmode"]
        )
