"""Test paper config manager."""

import typing as tp
import unittest
import unittest.mock as mock
from collections import defaultdict
from pathlib import Path
from tempfile import NamedTemporaryFile

from benchbuild.source import nosource
from benchbuild.utils.revision_ranges import block_revisions, SingleRevision
from test_case_study import YAML_CASE_STUDY

import varats.paper_mgmt.paper_config_manager as PCM
from tests.paper.test_case_study import mocked_create_lazy_commit_map_loader
from tests.test_utils import DummyGit
from varats.data.reports.commit_report import CommitReport
from varats.paper.case_study import load_case_study_from_file, CaseStudy
from varats.projects.c_projects.gzip import Gzip
from varats.report.report import FileStatusExtension
from varats.utils.git_util import ShortCommitHash


class TestPaperConfigManager(unittest.TestCase):
    """Test basic PaperConfigManager functionality."""

    DUMMY_GIT = DummyGit(remote="/dev/null", local="/dev/null")

    case_study: CaseStudy

    @classmethod
    def setUpClass(cls) -> None:
        """Setup case study from yaml doc."""
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
        self.mock_gzip.NAME = 'gzip'
        self.mock_gzip.SOURCE = [nosource()]

        project_util_patcher = mock.patch(
            'varats.paper_mgmt.case_study.get_project_cls_by_name'
        )
        self.addCleanup(project_util_patcher.stop)
        project_util_patcher.start().return_value = self.mock_gzip

        # allows to add blocked revisions
        project_source_patcher = mock.patch(
            'varats.revision.revisions.get_primary_project_source'
        )
        self.addCleanup(project_source_patcher.stop)
        self.project_source_mock = project_source_patcher.start()
        self.project_source_mock.return_value = self.DUMMY_GIT

    @mock.patch('varats.paper_mgmt.case_study.get_tagged_revisions')
    def test_short_status(self, mock_get_tagged_revisions) -> None:
        """Check if the case study can show a short status."""

        # block a revision
        mocked_gzip_source = block_revisions([SingleRevision("7620b81735")])(
            DummyGit(remote="/dev/null", local="/dev/null")
        )
        self.project_source_mock.return_value = mocked_gzip_source

        # Revision not in set
        mock_get_tagged_revisions.return_value = [
            (ShortCommitHash('42b25e7f15'), FileStatusExtension.SUCCESS)
        ]

        status = PCM.get_short_status(self.case_study, CommitReport, 5)
        self.assertEqual(status, 'CS: gzip_1: (  0/10) processed [0/0/0/9/1]')
        mock_get_tagged_revisions.assert_called()

        mock_get_tagged_revisions.reset_mock()
        mock_get_tagged_revisions.return_value = [
            (ShortCommitHash('b8b25e7f15'), FileStatusExtension.SUCCESS)
        ]

        status = PCM.get_short_status(self.case_study, CommitReport, 5)
        self.assertEqual(status, 'CS: gzip_1: (  1/10) processed [1/0/0/8/1]')
        mock_get_tagged_revisions.assert_called()

    @mock.patch('varats.paper_mgmt.case_study.get_tagged_revisions')
    def test_short_status_color(self, mock_get_tagged_revisions) -> None:
        """
        Check if the case study can show a short status.

        Currently this only checks if the output is correctly generated but not
        if the colors are present.
        """
        # Revision not in set
        mock_get_tagged_revisions.return_value = [
            (ShortCommitHash('42b25e7f15'), FileStatusExtension.SUCCESS)
        ]

        status = PCM.get_short_status(self.case_study, CommitReport, 5, True)
        self.assertEqual(status, 'CS: gzip_1: (  0/10) processed [0/0/0/10/0]')
        mock_get_tagged_revisions.assert_called()

        mock_get_tagged_revisions.reset_mock()
        mock_get_tagged_revisions.return_value = [
            (ShortCommitHash('b8b25e7f15'), FileStatusExtension.SUCCESS)
        ]

        status = PCM.get_short_status(self.case_study, CommitReport, 5, True)
        self.assertEqual(status, 'CS: gzip_1: (  1/10) processed [1/0/0/9/0]')
        mock_get_tagged_revisions.assert_called()

    @mock.patch(
        'varats.paper_mgmt.paper_config_manager.create_lazy_commit_map_loader',
        side_effect=mocked_create_lazy_commit_map_loader
    )
    @mock.patch('varats.paper_mgmt.case_study.get_tagged_revisions')
    def test_status(self, mock_get_tagged_revisions, mock_cmap_loader) -> None:
        # pylint: disable=unused-argument
        """Check if the case study can show a short status."""
        # Revision not in set
        mock_get_tagged_revisions.return_value = [
            (ShortCommitHash('42b25e7f15'), FileStatusExtension.SUCCESS)
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
            (ShortCommitHash('b8b25e7f15'), FileStatusExtension.SUCCESS),
            (ShortCommitHash('622e9b1d02'), FileStatusExtension.FAILED),
            (ShortCommitHash('1e7e3769dc'), FileStatusExtension.COMPILE_ERROR),
            (ShortCommitHash('2e654f9963'), FileStatusExtension.BLOCKED)
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
            (ShortCommitHash('b8b25e7f15'), FileStatusExtension.SUCCESS),
            (ShortCommitHash('622e9b1d02'), FileStatusExtension.FAILED),
            (ShortCommitHash('1e7e3769dc'), FileStatusExtension.COMPILE_ERROR),
            (ShortCommitHash('2e654f9963'), FileStatusExtension.BLOCKED)
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
        'varats.paper_mgmt.paper_config_manager.create_lazy_commit_map_loader',
        side_effect=mocked_create_lazy_commit_map_loader
    )
    @mock.patch('varats.paper_mgmt.case_study.get_tagged_revisions')
    def test_status_with_stages(
        self, mock_get_tagged_revisions, mock_cmap_loader
    ) -> None:
        # pylint: disable=unused-argument
        """Check if the case study can show a short status."""
        # Revision not in set
        mock_get_tagged_revisions.return_value = [
            (ShortCommitHash('42b25e7f15'), FileStatusExtension.SUCCESS)
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
            (ShortCommitHash('b8b25e7f15'), FileStatusExtension.SUCCESS),
            (ShortCommitHash('622e9b1d02'), FileStatusExtension.FAILED),
            (ShortCommitHash('1e7e3769dc'), FileStatusExtension.COMPILE_ERROR),
            (ShortCommitHash('2e654f9963'), FileStatusExtension.BLOCKED)
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
            (ShortCommitHash('b8b25e7f15'), FileStatusExtension.SUCCESS),
            (ShortCommitHash('622e9b1d02'), FileStatusExtension.FAILED),
            (ShortCommitHash('1e7e3769dc'), FileStatusExtension.COMPILE_ERROR),
            (ShortCommitHash('2e654f9963'), FileStatusExtension.BLOCKED)
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

    @mock.patch('varats.paper_mgmt.case_study.get_tagged_revisions')
    def test_status_color(self, mock_get_tagged_revisions) -> None:
        """
        Check if the case study can show a short status.

        Currently this only checks if the output is correctly generated but not
        if the colors are present.
        """
        # Revision not in set
        mock_get_tagged_revisions.return_value = [
            (ShortCommitHash('42b25e7f15'), FileStatusExtension.SUCCESS)
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
            (ShortCommitHash('b8b25e7f15'), FileStatusExtension.SUCCESS),
            (ShortCommitHash('622e9b1d02'), FileStatusExtension.FAILED),
            (ShortCommitHash('1e7e3769dc'), FileStatusExtension.COMPILE_ERROR),
            (ShortCommitHash('2e654f9963'), FileStatusExtension.BLOCKED)
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

    def test_legend(self) -> None:
        """
        Check if the paper manager produces the correct legend.

        Currently this only checks if the output is correctly generated but not
        if the colors are present.
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

    @mock.patch('varats.paper_mgmt.case_study.get_tagged_revisions')
    def test_total_status_color(self, mock_get_tagged_revisions) -> None:
        """Check if the total status is correctly generated."""
        total_status_occurrences: tp.DefaultDict[
            FileStatusExtension, tp.Set[ShortCommitHash]] = defaultdict(set)
        # Revision not in set
        mock_get_tagged_revisions.return_value = [
            (ShortCommitHash('42b25e7f15'), FileStatusExtension.SUCCESS)
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
            (ShortCommitHash('b8b25e7f15'), FileStatusExtension.SUCCESS),
            (ShortCommitHash('622e9b1d02'), FileStatusExtension.FAILED),
            (ShortCommitHash('1e7e3769dc'), FileStatusExtension.COMPILE_ERROR),
            (ShortCommitHash('2e654f9963'), FileStatusExtension.BLOCKED)
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
            (ShortCommitHash('b8b25e7f15'), FileStatusExtension.SUCCESS),
            (ShortCommitHash('622e9b1d02'), FileStatusExtension.FAILED),
            (ShortCommitHash('1e7e3769dc'), FileStatusExtension.COMPILE_ERROR),
            (ShortCommitHash('2e654f9963'), FileStatusExtension.BLOCKED)
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
