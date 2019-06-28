"""
Test paper config manager
"""

import unittest
import yaml
import mock

from varats.data.commit_report import CommitReport
import varats.paper.paper_config_manager as PCM

from test_case_study import YAML_CASE_STUDY


class TestPaperConfigManager(unittest.TestCase):
    """
    Test basic PaperConfigManager functionality.
    """

    @classmethod
    def setUpClass(cls):
        """
        Setup case study from yaml doc.
        """
        cls.case_study = yaml.safe_load(YAML_CASE_STUDY)

    @mock.patch('varats.paper.case_study.get_proccessed_revisions')
    def test_short_status(self, mock_get_processed_revision):
        """
        Check if the case study can show a short status.
        """
        # Revision not in set
        mock_get_processed_revision.return_value = ['42b25e7f15']

        status = PCM.get_short_status(self.case_study, CommitReport, 5)
        self.assertEqual(status, 'CS: gzip_1: (  0/10) processed [0/10/0]')
        mock_get_processed_revision.assert_called()

        # Revision not in set
        mock_get_processed_revision.reset_mock()
        mock_get_processed_revision.return_value = ['b8b25e7f15']

        status = PCM.get_short_status(self.case_study, CommitReport, 5)
        self.assertEqual(status, 'CS: gzip_1: (  1/10) processed [0/9/1]')
        mock_get_processed_revision.assert_called()

    @mock.patch('varats.paper.case_study.get_proccessed_revisions')
    def test_short_status_color(self, mock_get_processed_revision):
        """
        Check if the case study can show a short status.

        Currently this only checks if the output is correctly generated but
        not if the colors are present.
        """
        # Revision not in set
        mock_get_processed_revision.return_value = ['42b25e7f15']

        status = PCM.get_short_status(self.case_study, CommitReport, 5, True)
        self.assertEqual(status, 'CS: gzip_1: (  0/10) processed [0/10/0]')
        mock_get_processed_revision.assert_called()

        # Revision not in set
        mock_get_processed_revision.reset_mock()
        mock_get_processed_revision.return_value = ['b8b25e7f15']

        status = PCM.get_short_status(self.case_study, CommitReport, 5, True)
        self.assertEqual(status, 'CS: gzip_1: (  1/10) processed [0/9/1]')
        mock_get_processed_revision.assert_called()

    @mock.patch('varats.paper.case_study.get_proccessed_revisions')
    def test_status(self, mock_get_processed_revision):
        """
        Check if the case study can show a short status.
        """
        # Revision not in set
        mock_get_processed_revision.return_value = ['42b25e7f15']

        status = PCM.get_status(self.case_study, CommitReport, 5, False)
        self.assertEqual(
            status, """CS: gzip_1: (  0/10) processed [0/10/0]
    7620b81735 [Missing]
    622e9b1d02 [Missing]
    8798d5c4fd [Missing]
    2e654f9963 [Missing]
    edfad78619 [Missing]
    a3db5806d0 [Missing]
    e75f428c0d [Missing]
    1e7e3769dc [Missing]
    9872ba420c [Missing]
    b8b25e7f15 [Missing]
""")
        mock_get_processed_revision.assert_called()

        # Revision not in set
        mock_get_processed_revision.reset_mock()
        mock_get_processed_revision.return_value = ['b8b25e7f15', '2e654f9963']

        status = PCM.get_status(self.case_study, CommitReport, 5, False)
        self.assertEqual(
            status, """CS: gzip_1: (  2/10) processed [0/8/2]
    7620b81735 [Missing]
    622e9b1d02 [Missing]
    8798d5c4fd [Missing]
    2e654f9963 [OK]
    edfad78619 [Missing]
    a3db5806d0 [Missing]
    e75f428c0d [Missing]
    1e7e3769dc [Missing]
    9872ba420c [Missing]
    b8b25e7f15 [OK]
""")
        mock_get_processed_revision.assert_called()

    @mock.patch('varats.paper.case_study.get_proccessed_revisions')
    def test_status_with_stages(self, mock_get_processed_revision):
        """
        Check if the case study can show a short status.
        """
        # Revision not in set
        mock_get_processed_revision.return_value = ['42b25e7f15']

        status = PCM.get_status(self.case_study, CommitReport, 5, True)
        self.assertEqual(
            status, """CS: gzip_1: (  0/10) processed [0/10/0]
  Stage 0 (stage_0)
    7620b81735 [Missing]
    622e9b1d02 [Missing]
    8798d5c4fd [Missing]
    2e654f9963 [Missing]
    edfad78619 [Missing]
    a3db5806d0 [Missing]
    e75f428c0d [Missing]
    1e7e3769dc [Missing]
    9872ba420c [Missing]
    b8b25e7f15 [Missing]
  Stage 1
    7620b81735 [Missing]
""")
        mock_get_processed_revision.assert_called()

        # Revision not in set
        mock_get_processed_revision.reset_mock()
        mock_get_processed_revision.return_value = ['b8b25e7f15', '2e654f9963']

        status = PCM.get_status(self.case_study, CommitReport, 5, True)
        self.assertEqual(
            status, """CS: gzip_1: (  2/10) processed [0/8/2]
  Stage 0 (stage_0)
    7620b81735 [Missing]
    622e9b1d02 [Missing]
    8798d5c4fd [Missing]
    2e654f9963 [OK]
    edfad78619 [Missing]
    a3db5806d0 [Missing]
    e75f428c0d [Missing]
    1e7e3769dc [Missing]
    9872ba420c [Missing]
    b8b25e7f15 [OK]
  Stage 1
    7620b81735 [Missing]
""")
        mock_get_processed_revision.assert_called()

    @mock.patch('varats.paper.case_study.get_proccessed_revisions')
    def test_status_color(self, mock_get_processed_revision):
        """
        Check if the case study can show a short status.

        Currently this only checks if the output is correctly generated but
        not if the colors are present.
        """
        # Revision not in set
        mock_get_processed_revision.return_value = ['42b25e7f15']

        status = PCM.get_status(self.case_study, CommitReport, 5, False, True)
        self.assertEqual(
            status, """CS: gzip_1: (  0/10) processed [0/10/0]
    7620b81735 [Missing]
    622e9b1d02 [Missing]
    8798d5c4fd [Missing]
    2e654f9963 [Missing]
    edfad78619 [Missing]
    a3db5806d0 [Missing]
    e75f428c0d [Missing]
    1e7e3769dc [Missing]
    9872ba420c [Missing]
    b8b25e7f15 [Missing]
""")
        mock_get_processed_revision.assert_called()

        # Revision not in set
        mock_get_processed_revision.reset_mock()
        mock_get_processed_revision.return_value = ['b8b25e7f15', '2e654f9963']

        status = PCM.get_status(self.case_study, CommitReport, 5, False, True)
        self.assertEqual(
            status, """CS: gzip_1: (  2/10) processed [0/8/2]
    7620b81735 [Missing]
    622e9b1d02 [Missing]
    8798d5c4fd [Missing]
    2e654f9963 [OK]
    edfad78619 [Missing]
    a3db5806d0 [Missing]
    e75f428c0d [Missing]
    1e7e3769dc [Missing]
    9872ba420c [Missing]
    b8b25e7f15 [OK]
""")
        mock_get_processed_revision.assert_called()
