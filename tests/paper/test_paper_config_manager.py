"""
Test paper config manager
"""

import typing as tp
import unittest
from collections import defaultdict
from pathlib import Path
from tempfile import NamedTemporaryFile

import mock
from test_case_study import YAML_CASE_STUDY

import varats.paper.paper_config_manager as PCM
from tests.paper.test_case_study import mocked_create_lazy_commit_map_loader
from varats.data.report import FileStatusExtension
from varats.data.reports.commit_report import CommitReport
from varats.paper.case_study import load_case_study_from_file
from varats.projects.c_projects.gzip import Gzip


class TestPaperConfigManager(unittest.TestCase):
    """
    Test basic PaperConfigManager functionality.
    """

    @classmethod
    def setUpClass(cls):
        """
        Setup case study from yaml doc.
        """
        with NamedTemporaryFile('w') as yaml_file:
            yaml_file.write(YAML_CASE_STUDY)
            yaml_file.seek(0)
            cls.case_study = load_case_study_from_file(Path(yaml_file.name))

    def setUp(self) -> None:
        gzip_patcher = mock.patch(
            'varats.projects.c_projects.gzip.Gzip', spec=Gzip
        )
        self.addCleanup(gzip_patcher.stop)
        self.mock_gzip = gzip_patcher.start()
        self.mock_gzip.is_blocked_revision = lambda x: (False, "")

        project_util_patcher = mock.patch(
            'varats.paper.case_study.get_project_cls_by_name'
        )
        self.addCleanup(project_util_patcher.stop)
        self.mock_get_project = project_util_patcher.start()
        self.mock_get_project.return_value = self.mock_gzip

    @mock.patch('varats.paper.case_study.get_tagged_revisions')
    def test_short_status(self, mock_get_tagged_revisions):
        """
        Check if the case study can show a short status.
        """

        def is_blocked_revision(rev: str):
            if rev == "7620b81735":
                return True, ""
            return False, ""

        # block a revision
        self.mock_gzip.is_blocked_revision = is_blocked_revision
        # Revision not in set
        mock_get_tagged_revisions.return_value = [
            ('42b25e7f15', FileStatusExtension.Success)
        ]

        status = PCM.get_short_status(self.case_study, CommitReport, 5)
        self.assertEqual(status, 'CS: gzip_1: (  0/10) processed [0/0/0/9/1]')
        mock_get_tagged_revisions.assert_called()

        mock_get_tagged_revisions.reset_mock()
        mock_get_tagged_revisions.return_value = [
            ('b8b25e7f15', FileStatusExtension.Success)
        ]

        status = PCM.get_short_status(self.case_study, CommitReport, 5)
        self.assertEqual(status, 'CS: gzip_1: (  1/10) processed [1/0/0/8/1]')
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
        self.assertEqual(status, 'CS: gzip_1: (  0/10) processed [0/0/0/10/0]')
        mock_get_tagged_revisions.assert_called()

        mock_get_tagged_revisions.reset_mock()
        mock_get_tagged_revisions.return_value = [
            ('b8b25e7f15', FileStatusExtension.Success)
        ]

        status = PCM.get_short_status(self.case_study, CommitReport, 5, True)
        self.assertEqual(status, 'CS: gzip_1: (  1/10) processed [1/0/0/9/0]')
        mock_get_tagged_revisions.assert_called()

    @mock.patch(
        'varats.paper.paper_config_manager.create_lazy_commit_map_loader',
        side_effect=mocked_create_lazy_commit_map_loader
    )
    @mock.patch('varats.paper.case_study.get_tagged_revisions')
    def test_status(self, mock_get_tagged_revisions, mock_cmap_loader):
        # pylint: disable=unused-argument
        """
        Check if the case study can show a short status.
        """
        # Revision not in set
        mock_get_tagged_revisions.return_value = [
            ('42b25e7f15', FileStatusExtension.Success)
        ]

        status = PCM.get_status(self.case_study, CommitReport, 5, False, False)
        self.assertEqual(
            status, """CS: gzip_1: (  0/10) processed [0/0/0/10/0]
    b8b25e7f15 [Missing]
    7620b81735 [Missing]
    622e9b1d02 [Missing]
    8798d5c4fd [Missing]
    2e654f9963 [Missing]
    edfad78619 [Missing]
    a3db5806d0 [Missing]
    e75f428c0d [Missing]
    1e7e3769dc [Missing]
    9872ba420c [Missing]
"""
        )
        mock_get_tagged_revisions.assert_called()

        mock_get_tagged_revisions.reset_mock()
        mock_get_tagged_revisions.return_value = [
            ('b8b25e7f15', FileStatusExtension.Success),
            ('622e9b1d02', FileStatusExtension.Failed),
            ('1e7e3769dc', FileStatusExtension.CompileError),
            ('2e654f9963', FileStatusExtension.Blocked)
        ]

        status = PCM.get_status(self.case_study, CommitReport, 5, False, False)
        self.assertEqual(
            status, """CS: gzip_1: (  1/10) processed [1/1/1/6/1]
    b8b25e7f15 [Success]
    7620b81735 [Missing]
    622e9b1d02 [Failed]
    8798d5c4fd [Missing]
    2e654f9963 [Blocked]
    edfad78619 [Missing]
    a3db5806d0 [Missing]
    e75f428c0d [Missing]
    1e7e3769dc [CompileError]
    9872ba420c [Missing]
"""
        )
        mock_get_tagged_revisions.assert_called()

        mock_get_tagged_revisions.reset_mock()
        mock_get_tagged_revisions.return_value = [
            ('b8b25e7f15', FileStatusExtension.Success),
            ('622e9b1d02', FileStatusExtension.Failed),
            ('1e7e3769dc', FileStatusExtension.CompileError),
            ('2e654f9963', FileStatusExtension.Blocked)
        ]

        status = PCM.get_status(self.case_study, CommitReport, 5, False, True)
        self.assertEqual(
            status, """CS: gzip_1: (  1/10) processed [1/1/1/6/1]
    7620b81735 [Missing]
    622e9b1d02 [Failed]
    8798d5c4fd [Missing]
    2e654f9963 [Blocked]
    edfad78619 [Missing]
    a3db5806d0 [Missing]
    e75f428c0d [Missing]
    1e7e3769dc [CompileError]
    9872ba420c [Missing]
    b8b25e7f15 [Success]
"""
        )
        mock_get_tagged_revisions.assert_called()

    @mock.patch(
        'varats.paper.paper_config_manager.create_lazy_commit_map_loader',
        side_effect=mocked_create_lazy_commit_map_loader
    )
    @mock.patch('varats.paper.case_study.get_tagged_revisions')
    def test_status_with_stages(
        self, mock_get_tagged_revisions, mock_cmap_loader
    ):
        # pylint: disable=unused-argument
        """
        Check if the case study can show a short status.
        """
        # Revision not in set
        mock_get_tagged_revisions.return_value = [
            ('42b25e7f15', FileStatusExtension.Success)
        ]

        status = PCM.get_status(self.case_study, CommitReport, 5, True, False)
        self.assertEqual(
            status, """CS: gzip_1: (  0/10) processed [0/0/0/10/0]
  Stage 0 (stage_0)
    b8b25e7f15 [Missing]
    7620b81735 [Missing]
    622e9b1d02 [Missing]
    8798d5c4fd [Missing]
    2e654f9963 [Missing]
    edfad78619 [Missing]
    a3db5806d0 [Missing]
    e75f428c0d [Missing]
    1e7e3769dc [Missing]
    9872ba420c [Missing]
  Stage 1
    7620b81735 [Missing]
"""
        )
        mock_get_tagged_revisions.assert_called()

        mock_get_tagged_revisions.reset_mock()
        mock_get_tagged_revisions.return_value = [
            ('b8b25e7f15', FileStatusExtension.Success),
            ('622e9b1d02', FileStatusExtension.Failed),
            ('1e7e3769dc', FileStatusExtension.CompileError),
            ('2e654f9963', FileStatusExtension.Blocked)
        ]

        status = PCM.get_status(self.case_study, CommitReport, 5, True, False)
        self.assertEqual(
            status, """CS: gzip_1: (  1/10) processed [1/1/1/6/1]
  Stage 0 (stage_0)
    b8b25e7f15 [Success]
    7620b81735 [Missing]
    622e9b1d02 [Failed]
    8798d5c4fd [Missing]
    2e654f9963 [Blocked]
    edfad78619 [Missing]
    a3db5806d0 [Missing]
    e75f428c0d [Missing]
    1e7e3769dc [CompileError]
    9872ba420c [Missing]
  Stage 1
    7620b81735 [Missing]
"""
        )
        mock_get_tagged_revisions.assert_called()

        mock_get_tagged_revisions.reset_mock()
        mock_get_tagged_revisions.return_value = [
            ('b8b25e7f15', FileStatusExtension.Success),
            ('622e9b1d02', FileStatusExtension.Failed),
            ('1e7e3769dc', FileStatusExtension.CompileError),
            ('2e654f9963', FileStatusExtension.Blocked)
        ]

        status = PCM.get_status(self.case_study, CommitReport, 5, True, True)
        self.assertEqual(
            status, """CS: gzip_1: (  1/10) processed [1/1/1/6/1]
  Stage 0 (stage_0)
    7620b81735 [Missing]
    622e9b1d02 [Failed]
    8798d5c4fd [Missing]
    2e654f9963 [Blocked]
    edfad78619 [Missing]
    a3db5806d0 [Missing]
    e75f428c0d [Missing]
    1e7e3769dc [CompileError]
    9872ba420c [Missing]
    b8b25e7f15 [Success]
  Stage 1
    7620b81735 [Missing]
"""
        )
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

        status = PCM.get_status(
            self.case_study, CommitReport, 5, False, False, True
        )
        self.assertEqual(
            status, """CS: gzip_1: (  0/10) processed [0/0/0/10/0]
    b8b25e7f15 [Missing]
    7620b81735 [Missing]
    622e9b1d02 [Missing]
    8798d5c4fd [Missing]
    2e654f9963 [Missing]
    edfad78619 [Missing]
    a3db5806d0 [Missing]
    e75f428c0d [Missing]
    1e7e3769dc [Missing]
    9872ba420c [Missing]
"""
        )
        mock_get_tagged_revisions.assert_called()

        mock_get_tagged_revisions.reset_mock()
        mock_get_tagged_revisions.return_value = [
            ('b8b25e7f15', FileStatusExtension.Success),
            ('622e9b1d02', FileStatusExtension.Failed),
            ('1e7e3769dc', FileStatusExtension.CompileError),
            ('2e654f9963', FileStatusExtension.Blocked)
        ]

        status = PCM.get_status(
            self.case_study, CommitReport, 5, False, False, True
        )
        self.assertEqual(
            status, """CS: gzip_1: (  1/10) processed [1/1/1/6/1]
    b8b25e7f15 [Success]
    7620b81735 [Missing]
    622e9b1d02 [Failed]
    8798d5c4fd [Missing]
    2e654f9963 [Blocked]
    edfad78619 [Missing]
    a3db5806d0 [Missing]
    e75f428c0d [Missing]
    1e7e3769dc [CompileError]
    9872ba420c [Missing]
"""
        )
        mock_get_tagged_revisions.assert_called()

    def test_legend(self):
        """
        Check if the paper manager produces the correct legend.

        Currently this only checks if the output is correctly generated but
        not if the colors are present.
        """
        # pylint: disable=line-too-long
        self.assertEqual(
            PCM.get_legend(True),
            """CS: project_42: (Success / Total) processed [Success/Failed/CompileError/Missing/Blocked]
"""
        )

        self.assertEqual(
            PCM.get_legend(False),
            """CS: project_42: (Success / Total) processed [Success/Failed/CompileError/Missing/Blocked]
"""
        )

    @mock.patch('varats.paper.case_study.get_tagged_revisions')
    def test_total_status_color(self, mock_get_tagged_revisions):
        """
        Check if the total status is correctly generated.
        """
        total_status_occurrences: tp.DefaultDict[
            FileStatusExtension, tp.Set[str]] = defaultdict(set)
        # Revision not in set
        mock_get_tagged_revisions.return_value = [
            ('42b25e7f15', FileStatusExtension.Success)
        ]

        PCM.get_status(
            self.case_study, CommitReport, 5, False, False, True,
            total_status_occurrences
        )
        status = PCM.get_total_status(total_status_occurrences, 15, True)
        self.assertEqual(
            status,
            """--------------------------------------------------------------------------------
Total:         (  0/10) processed [0/0/0/10/0]"""
        )

        mock_get_tagged_revisions.assert_called()

        mock_get_tagged_revisions.reset_mock()
        mock_get_tagged_revisions.return_value = [
            ('b8b25e7f15', FileStatusExtension.Success),
            ('622e9b1d02', FileStatusExtension.Failed),
            ('1e7e3769dc', FileStatusExtension.CompileError),
            ('2e654f9963', FileStatusExtension.Blocked)
        ]

        PCM.get_status(
            self.case_study, CommitReport, 5, False, False, True,
            total_status_occurrences
        )
        status = PCM.get_total_status(total_status_occurrences, 15, True)
        self.assertEqual(
            status,
            """--------------------------------------------------------------------------------
Total:         (  1/14) processed [1/1/1/10/1]"""
        )

        mock_get_tagged_revisions.assert_called()

        # Care: The second block is duplicated to check if we prevent
        # adding the same revisions twice

        mock_get_tagged_revisions.reset_mock()
        mock_get_tagged_revisions.return_value = [
            ('b8b25e7f15', FileStatusExtension.Success),
            ('622e9b1d02', FileStatusExtension.Failed),
            ('1e7e3769dc', FileStatusExtension.CompileError),
            ('2e654f9963', FileStatusExtension.Blocked)
        ]

        PCM.get_status(
            self.case_study, CommitReport, 5, False, False, True,
            total_status_occurrences
        )
        status = PCM.get_total_status(total_status_occurrences, 15, True)
        self.assertEqual(
            status,
            """--------------------------------------------------------------------------------
Total:         (  1/14) processed [1/1/1/10/1]"""
        )

        mock_get_tagged_revisions.assert_called()
