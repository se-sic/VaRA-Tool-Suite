"""Test VaRA Experiment utilities."""
import tempfile
import typing as tp
import unittest
import unittest.mock as mock
from pathlib import Path

import benchbuild.utils.actions as actions
import benchbuild.utils.settings as s
from benchbuild.project import Project

import varats.utilss.experiment_util as EU
from tests.test_helper import BBTestSource
from tests.test_utils import get_test_config, replace_config, get_bb_test_config
from varats.data.reports.commit_report import CommitReport as CR
from varats.report.report import FileStatusExtension


class MockExperiment(EU.VersionExperiment):
    """Small MockExperiment to be used as a replacement for actual
    experiments."""

    NAME = "CommitReportExperiment"
    REPORT_TYPE = CR

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        return []


class BBTestProject(Project):
    """Test project for version sampling tests."""
    NAME = "test_empty"

    DOMAIN = "debug"
    GROUP = "debug"
    SOURCE = [
        BBTestSource(
            test_versions=['rev1', 'rev2', 'rev3', 'rev4', 'rev5'],
            local="test_source",
            remote="test_remote"
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
        cls.tmp_path = tempfile.TemporaryDirectory()
        cls.test_config = get_test_config(Path(cls.tmp_path.name))
        cls.test_config['experiment'] = {
            "file_status_blacklist": {
                "default": [],
            },
            "file_status_whitelist": {
                "default": [],
            },
            "random_order": {
                "default": False,
            },
            "sample_limit": {
                "default": None,
            },
        }
        s.setup_config(cls.test_config)
        cls.test_bb_config = get_bb_test_config()
        cls.vers_expr = MockExperiment()
        cls.rev_list = ['rev1', 'rev2', 'rev3', 'rev4', 'rev5']

    @classmethod
    def tearDownClass(cls):
        cls.tmp_path.cleanup()

    def setUp(self):
        """Set config to initial values."""
        self.test_config["experiment"]["sample_limit"] = None
        self.test_config["experiment"]["random_order"] = False
        self.test_config["experiment"]["file_status_whitelist"] = []
        self.test_config["experiment"]["file_status_blacklist"] = []
        self.test_bb_config["versions"]["full"] = False
        self.rev_list = ['rev1', 'rev2', 'rev3', 'rev4', 'rev5']

    @staticmethod
    def generate_get_tagged_revisions_output(
    ) -> tp.List[tp.Tuple[str, FileStatusExtension]]:
        """Generate get_tagged_revisions output for mocking."""
        return [('rev1', FileStatusExtension.Success),
                ('rev2', FileStatusExtension.Blocked),
                ('rev3', FileStatusExtension.CompileError),
                ('rev4', FileStatusExtension.Failed),
                ('rev5', FileStatusExtension.Missing)]

    def test_sample_limit(self):
        """Test if base_hash is loaded correctly."""
        with replace_config(vara_config=self.test_config) as config:
            self.assertEqual(config["experiment"]["sample_limit"].value, None)
            self.assertEqual(
                # pylint: disable=protected-access
                self.vers_expr._sample_num_versions(self.rev_list),
                self.rev_list
            )

            config["experiment"]["sample_limit"] = 3
            self.assertEqual(
                len(self.vers_expr._sample_num_versions(self.rev_list)), 3
            )

    def test_without_versions(self):
        """Test if we get the correct revision if no VaRA modifications are
        enabled."""
        sample_gen = self.vers_expr.sample(BBTestProject)
        self.assertEqual(sample_gen[0]["test_source"].version, "rev1")
        self.assertEqual(len(sample_gen), 1)

    @mock.patch('varats.utilss.experiment_util.get_tagged_revisions')
    def test_only_whitelisting_one(self, mock_get_tagged_revisions):
        """Test if we can whitelist file status."""
        with replace_config(
            replace_bb_config=True, vara_config=self.test_config
        ) as (config, bb_config):
            bb_config["versions"]["full"] = True
            # Revision not in set
            mock_get_tagged_revisions.return_value = \
                self.generate_get_tagged_revisions_output()

            config["experiment"]["file_status_whitelist"] = ['success']

            sample_gen = self.vers_expr.sample(BBTestProject)

            self.assertEqual(sample_gen[0]["test_source"].version, "rev1")
            self.assertEqual(len(sample_gen), 1)
            mock_get_tagged_revisions.assert_called()

    @mock.patch('varats.utilss.experiment_util.get_tagged_revisions')
    def test_only_whitelisting_many(self, mock_get_tagged_revisions):
        """Test if we can whitelist file status."""
        with replace_config(
            replace_bb_config=True, vara_config=self.test_config
        ) as (config, bb_config):
            bb_config["versions"]["full"] = True
            # Revision not in set
            mock_get_tagged_revisions.return_value = \
                self.generate_get_tagged_revisions_output()

            config["experiment"]["file_status_whitelist"] = [
                'success', 'Failed', 'Missing'
            ]

            sample_gen = self.vers_expr.sample(BBTestProject)

            self.assertEqual(sample_gen[0]["test_source"].version, "rev1")
            self.assertEqual(sample_gen[1]["test_source"].version, "rev4")
            self.assertEqual(sample_gen[2]["test_source"].version, "rev5")
            self.assertEqual(len(sample_gen), 3)
            mock_get_tagged_revisions.assert_called()

    @mock.patch('varats.utilss.experiment_util.get_tagged_revisions')
    def test_only_blacklisting_one(self, mock_get_tagged_revisions):
        """Test if we can blacklist file status."""
        with replace_config(
            replace_bb_config=True, vara_config=self.test_config
        ) as (config, bb_config):
            bb_config["versions"]["full"] = True
            # Revision not in set
            mock_get_tagged_revisions.return_value = \
                self.generate_get_tagged_revisions_output()

            config["experiment"]["file_status_blacklist"] = ['success']

            sample_gen = self.vers_expr.sample(BBTestProject)

            self.assertEqual(sample_gen[0]["test_source"].version, "rev2")
            self.assertEqual(sample_gen[1]["test_source"].version, "rev3")
            self.assertEqual(sample_gen[2]["test_source"].version, "rev4")
            self.assertEqual(sample_gen[3]["test_source"].version, "rev5")
            self.assertEqual(len(sample_gen), 4)
            mock_get_tagged_revisions.assert_called()

    @mock.patch('varats.utilss.experiment_util.get_tagged_revisions')
    def test_only_blacklisting_many(self, mock_get_tagged_revisions):
        """Test if we can blacklist file status."""
        with replace_config(
            replace_bb_config=True, vara_config=self.test_config
        ) as (config, bb_config):
            bb_config["versions"]["full"] = True
            # Revision not in set
            mock_get_tagged_revisions.return_value = \
                self.generate_get_tagged_revisions_output()

            config["experiment"]["file_status_blacklist"] = [
                'success', 'Failed', 'Blocked'
            ]

            sample_gen = self.vers_expr.sample(BBTestProject)

            self.assertEqual(sample_gen[0]["test_source"].version, "rev3")
            self.assertEqual(sample_gen[1]["test_source"].version, "rev5")
            self.assertEqual(len(sample_gen), 2)
            mock_get_tagged_revisions.assert_called()

    @mock.patch('varats.utilss.experiment_util.get_tagged_revisions')
    def test_white_overwrite_blacklisting(self, mock_get_tagged_revisions):
        """Test if whitelist overwrites blacklist."""
        with replace_config(
            replace_bb_config=True, vara_config=self.test_config
        ) as (config, bb_config):
            bb_config["versions"]["full"] = True
            # Revision not in set
            mock_get_tagged_revisions.return_value = \
                self.generate_get_tagged_revisions_output()

            config["experiment"]["file_status_blacklist"] = ['Failed']
            config["experiment"]["file_status_whitelist"] = ['Failed']

            sample_gen = self.vers_expr.sample(BBTestProject)

            self.assertEqual(sample_gen[0]["test_source"].version, "rev4")
            self.assertEqual(len(sample_gen), 1)
            mock_get_tagged_revisions.assert_called()
