"""Test VaRA Experiment utilities."""
import tempfile
import typing as tp
import unittest
import unittest.mock as mock

import benchbuild.utils.actions as actions
import benchbuild.utils.settings as s
from benchbuild.project import Project

import varats.experiment.experiment_util as EU
from tests.test_helper import BBTestSource
from tests.test_utils import run_in_test_environment
from varats.data.reports.commit_report import CommitReport as CR
from varats.report.report import FileStatusExtension, ReportSpecification
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import vara_cfg, bb_cfg


class MockExperiment(EU.VersionExperiment):
    """Small MockExperiment to be used as a replacement for actual
    experiments."""

    NAME = "CommitReportExperiment"
    REPORT_SPEC = ReportSpecification(CR)

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


class TestVersionExperiment(unittest.TestCase):
    """Test VersionExperiments sampling behaviour."""

    tmp_path: tempfile.TemporaryDirectory

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
    ) -> tp.List[tp.Tuple[ShortCommitHash, FileStatusExtension]]:
        """Generate get_tagged_revisions output for mocking."""
        return [
            (ShortCommitHash('rev1000000'), FileStatusExtension.SUCCESS),
            (ShortCommitHash('rev2000000'), FileStatusExtension.BLOCKED),
            (ShortCommitHash('rev3000000'), FileStatusExtension.COMPILE_ERROR),
            (ShortCommitHash('rev4000000'), FileStatusExtension.FAILED),
            (ShortCommitHash('rev5000000'), FileStatusExtension.MISSING)
        ]

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
        self.assertEqual(sample_gen[0]["test_source"].version, "rev1000000")
        self.assertEqual(len(sample_gen), 1)

    @run_in_test_environment()
    @mock.patch('varats.experiment.experiment_util.get_tagged_revisions')
    def test_only_whitelisting_one(self, mock_get_tagged_revisions):
        """Test if we can whitelist file status."""
        self.prepare_vara_config(vara_cfg())
        bb_cfg()["versions"]["full"] = True
        # Revision not in set
        mock_get_tagged_revisions.return_value = \
            self.generate_get_tagged_revisions_output()

        vara_cfg()["experiment"]["file_status_whitelist"] = ['success']

        sample_gen = self.vers_expr.sample(BBTestProject)

        self.assertEqual(sample_gen[0]["test_source"].version, "rev1000000")
        self.assertEqual(len(sample_gen), 1)
        mock_get_tagged_revisions.assert_called()

    @run_in_test_environment()
    @mock.patch('varats.experiment.experiment_util.get_tagged_revisions')
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

        self.assertEqual(sample_gen[0]["test_source"].version, "rev1000000")
        self.assertEqual(sample_gen[1]["test_source"].version, "rev4000000")
        self.assertEqual(sample_gen[2]["test_source"].version, "rev5000000")
        self.assertEqual(len(sample_gen), 3)
        mock_get_tagged_revisions.assert_called()

    @run_in_test_environment()
    @mock.patch('varats.experiment.experiment_util.get_tagged_revisions')
    def test_only_blacklisting_one(self, mock_get_tagged_revisions):
        """Test if we can blacklist file status."""
        self.prepare_vara_config(vara_cfg())
        bb_cfg()["versions"]["full"] = True
        # Revision not in set
        mock_get_tagged_revisions.return_value = \
            self.generate_get_tagged_revisions_output()

        vara_cfg()["experiment"]["file_status_blacklist"] = ['success']

        sample_gen = self.vers_expr.sample(BBTestProject)

        self.assertEqual(sample_gen[0]["test_source"].version, "rev2000000")
        self.assertEqual(sample_gen[1]["test_source"].version, "rev3000000")
        self.assertEqual(sample_gen[2]["test_source"].version, "rev4000000")
        self.assertEqual(sample_gen[3]["test_source"].version, "rev5000000")
        self.assertEqual(len(sample_gen), 4)
        mock_get_tagged_revisions.assert_called()

    @run_in_test_environment()
    @mock.patch('varats.experiment.experiment_util.get_tagged_revisions')
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

        self.assertEqual(sample_gen[0]["test_source"].version, "rev3000000")
        self.assertEqual(sample_gen[1]["test_source"].version, "rev5000000")
        self.assertEqual(len(sample_gen), 2)
        mock_get_tagged_revisions.assert_called()

    @run_in_test_environment()
    @mock.patch('varats.experiment.experiment_util.get_tagged_revisions')
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

        self.assertEqual(sample_gen[0]["test_source"].version, "rev4000000")
        self.assertEqual(len(sample_gen), 1)
        mock_get_tagged_revisions.assert_called()
