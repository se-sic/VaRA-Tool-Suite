"""
Test paper config manager
"""

import typing as tp
from collections import defaultdict
import unittest
import yaml
import mock

from varats.data.report import FileStatusExtension
from varats.data.reports.commit_report import CommitReport
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

    @mock.patch('varats.paper.case_study.get_tagged_revisions')
    def test_short_status(self, mock_get_tagged_revisions):
        """
        Check if the case study can show a short status.
        """
        # Revision not in set
        mock_get_tagged_revisions.return_value = [
            ('42b25e7f15', FileStatusExtension.Success)
        ]

        status = PCM.get_short_status(self.case_study, CommitReport, 5)
        self.assertEqual(status, 'CS: gzip_1: (  0/10) processed [0/0/0/10]')
        mock_get_tagged_revisions.assert_called()

        # Revision not in set
        mock_get_tagged_revisions.reset_mock()
        mock_get_tagged_revisions.return_value = [
            ('b8b25e7f15', FileStatusExtension.Success)
        ]

        status = PCM.get_short_status(self.case_study, CommitReport, 5)
        self.assertEqual(status, 'CS: gzip_1: (  1/10) processed [1/0/0/9]')
        mock_get_tagged_revisions.assert_called()

    @mock.patch('varats.paper.case_study.get_tagged_revisions')
    def test_short_status_color(self, mock_get_tagged_revisions):
        """
        Check if the case study can show a short status.

        Currently this only checks if the output is correctly generated but
        not if the colors are present.
        """
        # Revision not in set
        mock_get_tagged_revisions.return_value = [
            ('42b25e7f15', FileStatusExtension.Success)
        ]

        status = PCM.get_short_status(self.case_study, CommitReport, 5, True)
        self.assertEqual(status, 'CS: gzip_1: (  0/10) processed [0/0/0/10]')
        mock_get_tagged_revisions.assert_called()

        # Revision not in set
        mock_get_tagged_revisions.reset_mock()
        mock_get_tagged_revisions.return_value = [
            ('b8b25e7f15', FileStatusExtension.Success)
        ]

        status = PCM.get_short_status(self.case_study, CommitReport, 5, True)
        self.assertEqual(status, 'CS: gzip_1: (  1/10) processed [1/0/0/9]')
        mock_get_tagged_revisions.assert_called()

    @mock.patch('varats.paper.case_study.get_tagged_revisions')
    def test_status(self, mock_get_tagged_revisions):
        """
        Check if the case study can show a short status.
        """
        # Revision not in set
        mock_get_tagged_revisions.return_value = [
            ('42b25e7f15', FileStatusExtension.Success)
        ]

        status = PCM.get_status(self.case_study, CommitReport, 5, False)
        self.assertEqual(
            status, """CS: gzip_1: (  0/10) processed [0/0/0/10]
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
        mock_get_tagged_revisions.assert_called()

        # Revision not in set
        mock_get_tagged_revisions.reset_mock()
        mock_get_tagged_revisions.return_value = [
            ('b8b25e7f15', FileStatusExtension.Success),
            ('622e9b1d02', FileStatusExtension.Failed),
            ('1e7e3769dc', FileStatusExtension.CompileError),
            ('2e654f9963', FileStatusExtension.Success)
        ]

        status = PCM.get_status(self.case_study, CommitReport, 5, False)
        self.assertEqual(
            status, """CS: gzip_1: (  2/10) processed [2/1/1/6]
    7620b81735 [Missing]
    622e9b1d02 [Failed]
    8798d5c4fd [Missing]
    2e654f9963 [Success]
    edfad78619 [Missing]
    a3db5806d0 [Missing]
    e75f428c0d [Missing]
    1e7e3769dc [CompileError]
    9872ba420c [Missing]
    b8b25e7f15 [Success]
""")
        mock_get_tagged_revisions.assert_called()

    @mock.patch('varats.paper.case_study.get_tagged_revisions')
    def test_status_with_stages(self, mock_get_tagged_revisions):
        """
        Check if the case study can show a short status.
        """
        # Revision not in set
        mock_get_tagged_revisions.return_value = [
            ('42b25e7f15', FileStatusExtension.Success)
        ]

        status = PCM.get_status(self.case_study, CommitReport, 5, True)
        self.assertEqual(
            status, """CS: gzip_1: (  0/10) processed [0/0/0/10]
  Stage 0
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
        mock_get_tagged_revisions.assert_called()

        # Revision not in set
        mock_get_tagged_revisions.reset_mock()
        mock_get_tagged_revisions.return_value = [
            ('b8b25e7f15', FileStatusExtension.Success),
            ('622e9b1d02', FileStatusExtension.Failed),
            ('1e7e3769dc', FileStatusExtension.CompileError),
            ('2e654f9963', FileStatusExtension.Success)
        ]

        status = PCM.get_status(self.case_study, CommitReport, 5, True)
        self.assertEqual(
            status, """CS: gzip_1: (  2/10) processed [2/1/1/6]
  Stage 0
    7620b81735 [Missing]
    622e9b1d02 [Failed]
    8798d5c4fd [Missing]
    2e654f9963 [Success]
    edfad78619 [Missing]
    a3db5806d0 [Missing]
    e75f428c0d [Missing]
    1e7e3769dc [CompileError]
    9872ba420c [Missing]
    b8b25e7f15 [Success]
  Stage 1
    7620b81735 [Missing]
""")
        mock_get_tagged_revisions.assert_called()

    @mock.patch('varats.paper.case_study.get_tagged_revisions')
    def test_status_color(self, mock_get_tagged_revisions):
        """
        Check if the case study can show a short status.

        Currently this only checks if the output is correctly generated but
        not if the colors are present.
        """
        # Revision not in set
        mock_get_tagged_revisions.return_value = [
            ('42b25e7f15', FileStatusExtension.Success)
        ]

        status = PCM.get_status(self.case_study, CommitReport, 5, False, True)
        self.assertEqual(
            status, """CS: gzip_1: (  0/10) processed [0/0/0/10]
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
        mock_get_tagged_revisions.assert_called()

        # Revision not in set
        mock_get_tagged_revisions.reset_mock()
        mock_get_tagged_revisions.return_value = [
            ('b8b25e7f15', FileStatusExtension.Success),
            ('622e9b1d02', FileStatusExtension.Failed),
            ('1e7e3769dc', FileStatusExtension.CompileError),
            ('2e654f9963', FileStatusExtension.Success)
        ]

        status = PCM.get_status(self.case_study, CommitReport, 5, False, True)
        self.assertEqual(
            status, """CS: gzip_1: (  2/10) processed [2/1/1/6]
    7620b81735 [Missing]
    622e9b1d02 [Failed]
    8798d5c4fd [Missing]
    2e654f9963 [Success]
    edfad78619 [Missing]
    a3db5806d0 [Missing]
    e75f428c0d [Missing]
    1e7e3769dc [CompileError]
    9872ba420c [Missing]
    b8b25e7f15 [Success]
""")
        mock_get_tagged_revisions.assert_called()

    def test_legend(self):
        """
        Check if the paper manager produces the correct legend.

        Currently this only checks if the output is correctly generated but
        not if the colors are present.
        """
        self.assertEqual(
            PCM.get_legend(True),
            """CS: project_42: (Success / Total) processed [Success/Failed/CompileError/Missing]
"""
        )

        self.assertEqual(
            PCM.get_legend(False),
            """CS: project_42: (Success / Total) processed [Success/Failed/CompileError/Missing]
"""
        )

    @mock.patch('varats.paper.case_study.get_tagged_revisions')
    def test_total_status_color(self, mock_get_tagged_revisions):
        """
        Check if the total status is correctly generated.
        """
        total_status_occurrences: tp.DefaultDict[FileStatusExtension, tp.
                                                 Set[str]] = defaultdict(set)
        # Revision not in set
        mock_get_tagged_revisions.return_value = [
            ('42b25e7f15', FileStatusExtension.Success)
        ]

        PCM.get_status(self.case_study, CommitReport, 5, False, True,
                       total_status_occurrences)
        status = PCM.get_total_status(total_status_occurrences, 15, True)
        self.assertEqual(
            status,
            """--------------------------------------------------------------------------------
Total:         (  0/10) processed [0/0/0/10]""")

        mock_get_tagged_revisions.assert_called()

        # Revision not in set
        mock_get_tagged_revisions.reset_mock()
        mock_get_tagged_revisions.return_value = [
            ('b8b25e7f15', FileStatusExtension.Success),
            ('622e9b1d02', FileStatusExtension.Failed),
            ('1e7e3769dc', FileStatusExtension.CompileError),
            ('2e654f9963', FileStatusExtension.Success)
        ]

        PCM.get_status(self.case_study, CommitReport, 5, False, True,
                       total_status_occurrences)
        status = PCM.get_total_status(total_status_occurrences, 15, True)
        self.assertEqual(
            status,
            """--------------------------------------------------------------------------------
Total:         (  2/14) processed [2/1/1/10]""")

        mock_get_tagged_revisions.assert_called()

        # Care: The second block is duplicated to check if we prevent
        # adding the same revisions twice

        # Revision not in set
        mock_get_tagged_revisions.reset_mock()
        mock_get_tagged_revisions.return_value = [
            ('b8b25e7f15', FileStatusExtension.Success),
            ('622e9b1d02', FileStatusExtension.Failed),
            ('1e7e3769dc', FileStatusExtension.CompileError),
            ('2e654f9963', FileStatusExtension.Success)
        ]

        PCM.get_status(self.case_study, CommitReport, 5, False, True,
                       total_status_occurrences)
        status = PCM.get_total_status(total_status_occurrences, 15, True)
        self.assertEqual(
            status,
            """--------------------------------------------------------------------------------
Total:         (  2/14) processed [2/1/1/10]""")

        mock_get_tagged_revisions.assert_called()
