"""Test paper config manager."""

import typing as tp
import unittest
import unittest.mock as mock
from collections import defaultdict
from itertools import cycle
from pathlib import Path
from tempfile import NamedTemporaryFile

from benchbuild.source import nosource
from benchbuild.utils.revision_ranges import block_revisions, SingleRevision
from pygtrie import CharTrie

import varats.paper_mgmt.paper_config_manager as PCM
from tests.paper.test_case_study import YAML_CASE_STUDY
from tests.test_utils import DummyGit
from tests.utils.test_experiment_util import (
    MockExperiment,
    MockExperimentMultiReport,
)
from varats.mapping.commit_map import CommitMap
from varats.paper.case_study import load_case_study_from_file, CaseStudy
from varats.projects.c_projects.gzip import Gzip
from varats.report.report import FileStatusExtension
from varats.utils.git_util import ShortCommitHash

GIT_LOG_OUT = """7620b817357d6f14356afd004ace2da426cf8c36
622e9b1d024da1343b83fc47fb1891e1d245add3
8798d5c4fd520dcf91f36ebfa60bc5f3dca550d9
2e654f9963154e5af9d3081fc871d54d783a1270
edfad78619d52479e02228a5789a2e98d7b0f9f6
a3db5806d012082b9e25cc36d09f19cd736a468f
e75f428c0ddc90a7011cfda82a7114a16c537e34
1e7e3769dc4efd55249c475470152acbcf804bb3
9872ba420c99323195e96cafe56ff247c3011ad5
b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a"""


class MockCommitMap(CommitMap):

    def __init__(self, stream: tp.Iterable[str]) -> None:
        self._hash_to_id: CharTrie = CharTrie()
        self._hash_to_id_master: CharTrie = CharTrie()
        for line in stream:
            slices = line.strip().split(', ')
            self._hash_to_id[slices[1]] = int(slices[0])
            self._hash_to_id_master[slices[1]] = int(slices[0])


def mocked_get_commit_map(
    project_name: str,  # pylint: disable=unused-argument
    cmap_path: tp.Optional[Path] = None,  # pylint: disable=unused-argument
    end: str = "HEAD",  # pylint: disable=unused-argument
    start: tp.Optional[str] = None
) -> CommitMap:  # pylint: disable=unused-argument
    """
    Create a dummy commit map.

    Args:
        project_name: name of the project
        cmap_path: path to commit map file
        end: commit to end loading, e.g, HEAD
        start: commit from which to start loading
    """

    def format_stream() -> tp.Generator[str, None, None]:
        for number, line in enumerate(reversed(GIT_LOG_OUT.split('\n'))):
            yield f"{number}, {line}\n"

    return MockCommitMap(format_stream())


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
    def test_short_status(
        self, mock_get_tagged_experiment_specific_revisions
    ) -> None:
        """Check if the case study can show a short status."""

        # block a revision
        mocked_gzip_source = block_revisions([SingleRevision("7620b81735")])(
            DummyGit(remote="/dev/null", local="/dev/null")
        )
        self.project_source_mock.return_value = mocked_gzip_source

        # Revision not in set
        mock_get_tagged_experiment_specific_revisions.return_value = {
            ShortCommitHash('42b25e7f15'): {
                None: FileStatusExtension.SUCCESS
            }
        }

        status = PCM.get_short_status(self.case_study, MockExperiment, 5)
        self.assertEqual(
            status, 'CS: gzip_1: (  0/10) processed [0/0/0/0/0/9/1]'
        )
        mock_get_tagged_experiment_specific_revisions.assert_called()

        mock_get_tagged_experiment_specific_revisions.reset_mock()
        mock_get_tagged_experiment_specific_revisions.return_value = {
            ShortCommitHash('9872ba420c'): {
                None: FileStatusExtension.SUCCESS
            }
        }

        status = PCM.get_short_status(self.case_study, MockExperiment, 5)
        self.assertEqual(
            status, 'CS: gzip_1: (  1/10) processed [1/0/0/0/0/8/1]'
        )
        mock_get_tagged_experiment_specific_revisions.assert_called()

    @mock.patch('varats.paper_mgmt.case_study.get_tagged_revisions')
    def test_short_status_color(
        self, mock_get_tagged_experiment_specific_revisions
    ) -> None:
        """
        Check if the case study can show a short status.

        Currently this only checks if the output is correctly generated but not
        if the colors are present.
        """
        # Revision not in set
        mock_get_tagged_experiment_specific_revisions.return_value = {
            ShortCommitHash('42b25e7f15'): {
                None: FileStatusExtension.SUCCESS
            }
        }

        status = PCM.get_short_status(self.case_study, MockExperiment, 5, True)
        self.assertEqual(
            status, 'CS: gzip_1: (  0/10) processed [0/0/0/0/0/10/0]'
        )
        mock_get_tagged_experiment_specific_revisions.assert_called()

        mock_get_tagged_experiment_specific_revisions.reset_mock()
        mock_get_tagged_experiment_specific_revisions.return_value = {
            ShortCommitHash('9872ba420c'): {
                None: FileStatusExtension.SUCCESS
            }
        }

        status = PCM.get_short_status(self.case_study, MockExperiment, 5, True)
        self.assertEqual(
            status, 'CS: gzip_1: (  1/10) processed [1/0/0/0/0/9/0]'
        )
        mock_get_tagged_experiment_specific_revisions.assert_called()

    @mock.patch(
        'varats.paper_mgmt.paper_config_manager.get_commit_map',
        side_effect=mocked_get_commit_map
    )
    @mock.patch('varats.paper_mgmt.case_study.get_tagged_revisions')
    def test_status(
        self, mock_get_tagged_experiment_specific_revisions, mock_cmap
    ) -> None:
        # pylint: disable=unused-argument
        """Check if the case study can show a short status."""
        # Revision not in set
        mock_get_tagged_experiment_specific_revisions.return_value = {
            ShortCommitHash('42b25e7f15'): {
                None: FileStatusExtension.SUCCESS
            }
        }

        status = PCM.get_status(
            self.case_study, MockExperiment, 5, False, False
        )
        self.assertEqual(
            status, """CS: gzip_1: (  0/10) processed [0/0/0/0/0/10/0]
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
        mock_get_tagged_experiment_specific_revisions.assert_called()

        mock_get_tagged_experiment_specific_revisions.reset_mock()
        mock_get_tagged_experiment_specific_revisions.side_effect = cycle([{
            ShortCommitHash('9872ba420c'): {
                None: FileStatusExtension.SUCCESS
            },
            ShortCommitHash('b8b25e7f15'): {
                0: FileStatusExtension.SUCCESS
            },
            ShortCommitHash('a3db5806d0'): {
                None: FileStatusExtension.SUCCESS
            },
            ShortCommitHash('622e9b1d02'): {
                None: FileStatusExtension.FAILED
            },
            ShortCommitHash('1e7e3769dc'): {
                None: FileStatusExtension.COMPILE_ERROR
            },
            ShortCommitHash('2e654f9963'): {
                None: FileStatusExtension.BLOCKED
            }
        }, {
            ShortCommitHash('9872ba420c'): {
                None: FileStatusExtension.SUCCESS
            }
        }])

        status = PCM.get_status(
            self.case_study, MockExperimentMultiReport, 5, False, False
        )
        self.assertEqual(
            status, """CS: gzip_1: (  1/10) processed [1/1/1/1/1/4/1]
    b8b25e7f15 [Partial]
    7620b81735 [Missing]
    622e9b1d02 [Failed]
    8798d5c4fd [Missing]
    2e654f9963 [Blocked]
    edfad78619 [Missing]
    a3db5806d0 [Incomplete]
    e75f428c0d [Missing]
    1e7e3769dc [CompileError]
    9872ba420c [Success]
"""
        )
        mock_get_tagged_experiment_specific_revisions.assert_called()

        mock_get_tagged_experiment_specific_revisions.reset_mock()

        status = PCM.get_status(
            self.case_study, MockExperimentMultiReport, 5, False, True
        )
        self.assertEqual(
            status, """CS: gzip_1: (  1/10) processed [1/1/1/1/1/4/1]
    7620b81735 [Missing]
    622e9b1d02 [Failed]
    8798d5c4fd [Missing]
    2e654f9963 [Blocked]
    edfad78619 [Missing]
    a3db5806d0 [Incomplete]
    e75f428c0d [Missing]
    1e7e3769dc [CompileError]
    9872ba420c [Success]
    b8b25e7f15 [Partial]
"""
        )
        mock_get_tagged_experiment_specific_revisions.assert_called()

    @mock.patch(
        'varats.paper_mgmt.paper_config_manager.get_commit_map',
        side_effect=mocked_get_commit_map
    )
    @mock.patch('varats.paper_mgmt.case_study.get_tagged_revisions')
    def test_status_with_stages(
        self, mock_get_tagged_experiment_specific_revisions, mock_cmap
    ) -> None:
        # pylint: disable=unused-argument
        """Check if the case study can show a short status."""
        # Revision not in set
        mock_get_tagged_experiment_specific_revisions.return_value = {
            ShortCommitHash('42b25e7f15'): {
                None: FileStatusExtension.SUCCESS
            }
        }

        status = PCM.get_status(self.case_study, MockExperiment, 5, True, False)
        self.assertEqual(
            status, """CS: gzip_1: (  0/10) processed [0/0/0/0/0/10/0]
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
        mock_get_tagged_experiment_specific_revisions.assert_called()

        mock_get_tagged_experiment_specific_revisions.reset_mock()
        mock_get_tagged_experiment_specific_revisions.side_effect = cycle([{
            ShortCommitHash('9872ba420c'): {
                None: FileStatusExtension.SUCCESS
            },
            ShortCommitHash('b8b25e7f15'): {
                0: FileStatusExtension.SUCCESS
            },
            ShortCommitHash('a3db5806d0'): {
                None: FileStatusExtension.SUCCESS
            },
            ShortCommitHash('622e9b1d02'): {
                None: FileStatusExtension.FAILED
            },
            ShortCommitHash('1e7e3769dc'): {
                None: FileStatusExtension.COMPILE_ERROR
            },
            ShortCommitHash('2e654f9963'): {
                None: FileStatusExtension.BLOCKED
            }
        }, {
            ShortCommitHash('9872ba420c'): {
                None: FileStatusExtension.SUCCESS
            }
        }])

        status = PCM.get_status(
            self.case_study, MockExperimentMultiReport, 5, True, False
        )
        self.assertEqual(
            status, """CS: gzip_1: (  1/10) processed [1/1/1/1/1/4/1]
  Stage 0 (stage_0)
    b8b25e7f15 [Partial]
    7620b81735 [Missing]
    622e9b1d02 [Failed]
    8798d5c4fd [Missing]
    2e654f9963 [Blocked]
    edfad78619 [Missing]
    a3db5806d0 [Incomplete]
    e75f428c0d [Missing]
    1e7e3769dc [CompileError]
    9872ba420c [Success]
  Stage 1
    7620b81735 [Missing]
"""
        )
        mock_get_tagged_experiment_specific_revisions.assert_called()

        mock_get_tagged_experiment_specific_revisions.reset_mock()

        status = PCM.get_status(
            self.case_study, MockExperimentMultiReport, 5, True, True
        )
        self.assertEqual(
            status, """CS: gzip_1: (  1/10) processed [1/1/1/1/1/4/1]
  Stage 0 (stage_0)
    7620b81735 [Missing]
    622e9b1d02 [Failed]
    8798d5c4fd [Missing]
    2e654f9963 [Blocked]
    edfad78619 [Missing]
    a3db5806d0 [Incomplete]
    e75f428c0d [Missing]
    1e7e3769dc [CompileError]
    9872ba420c [Success]
    b8b25e7f15 [Partial]
  Stage 1
    7620b81735 [Missing]
"""
        )
        mock_get_tagged_experiment_specific_revisions.assert_called()

    @mock.patch('varats.paper_mgmt.case_study.get_tagged_revisions')
    def test_status_color(
        self, mock_get_tagged_experiment_specific_revisions
    ) -> None:
        """
        Check if the case study can show a short status.

        Currently this only checks if the output is correctly generated but not
        if the colors are present.
        """
        # Revision not in set
        mock_get_tagged_experiment_specific_revisions.return_value = {
            ShortCommitHash('42b25e7f15'): {
                None: FileStatusExtension.SUCCESS
            }
        }

        status = PCM.get_status(
            self.case_study, MockExperiment, 5, False, False, True
        )
        self.assertEqual(
            status, """CS: gzip_1: (  0/10) processed [0/0/0/0/0/10/0]
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
        mock_get_tagged_experiment_specific_revisions.assert_called()

        mock_get_tagged_experiment_specific_revisions.reset_mock()
        mock_get_tagged_experiment_specific_revisions.side_effect = cycle([{
            ShortCommitHash('9872ba420c'): {
                None: FileStatusExtension.SUCCESS
            },
            ShortCommitHash('b8b25e7f15'): {
                0: FileStatusExtension.SUCCESS
            },
            ShortCommitHash('a3db5806d0'): {
                None: FileStatusExtension.SUCCESS
            },
            ShortCommitHash('622e9b1d02'): {
                None: FileStatusExtension.FAILED
            },
            ShortCommitHash('1e7e3769dc'): {
                None: FileStatusExtension.COMPILE_ERROR
            },
            ShortCommitHash('2e654f9963'): {
                None: FileStatusExtension.BLOCKED
            }
        }, {
            ShortCommitHash('9872ba420c'): {
                None: FileStatusExtension.SUCCESS
            }
        }])

        status = PCM.get_status(
            self.case_study, MockExperimentMultiReport, 5, False, False, True
        )
        self.assertEqual(
            status, """CS: gzip_1: (  1/10) processed [1/1/1/1/1/4/1]
    b8b25e7f15 [Partial]
    7620b81735 [Missing]
    622e9b1d02 [Failed]
    8798d5c4fd [Missing]
    2e654f9963 [Blocked]
    edfad78619 [Missing]
    a3db5806d0 [Incomplete]
    e75f428c0d [Missing]
    1e7e3769dc [CompileError]
    9872ba420c [Success]
"""
        )
        mock_get_tagged_experiment_specific_revisions.assert_called()

    def test_legend(self) -> None:
        """
        Check if the paper manager produces the correct legend.

        Currently this only checks if the output is correctly generated but not
        if the colors are present.
        """
        # pylint: disable=line-too-long
        self.assertEqual(
            PCM.get_legend(True),
            """CS: project_42: (Success / Total) processed [Success/Partial/Incomplete/Failed/CompileError/Missing/Blocked]
"""
        )

        self.assertEqual(
            PCM.get_legend(False),
            """CS: project_42: (Success / Total) processed [Success/Partial/Incomplete/Failed/CompileError/Missing/Blocked]
"""
        )

    @mock.patch('varats.paper_mgmt.case_study.get_tagged_revisions')
    def test_total_status_color(
        self, mock_get_tagged_experiment_specific_revisions
    ) -> None:
        """Check if the total status is correctly generated."""
        total_status_occurrences: tp.DefaultDict[
            FileStatusExtension, tp.Set[ShortCommitHash]] = defaultdict(set)
        # Revision not in set
        mock_get_tagged_experiment_specific_revisions.return_value = {
            ShortCommitHash('42b25e7f15'): {
                None: FileStatusExtension.SUCCESS
            }
        }

        PCM.get_status(
            self.case_study, MockExperiment, 5, False, False, True,
            total_status_occurrences
        )
        status = PCM.get_total_status(total_status_occurrences, 15, True)
        self.assertEqual(
            status,
            """--------------------------------------------------------------------------------
Total:         (  0/10) processed [0/0/0/0/0/10/0]"""
        )

        mock_get_tagged_experiment_specific_revisions.assert_called()

        mock_get_tagged_experiment_specific_revisions.reset_mock()
        mock_get_tagged_experiment_specific_revisions.side_effect = cycle([{
            ShortCommitHash('9872ba420c'): {
                None: FileStatusExtension.SUCCESS
            },
            ShortCommitHash('b8b25e7f15'): {
                0: FileStatusExtension.SUCCESS
            },
            ShortCommitHash('a3db5806d0'): {
                None: FileStatusExtension.SUCCESS
            },
            ShortCommitHash('622e9b1d02'): {
                None: FileStatusExtension.FAILED
            },
            ShortCommitHash('1e7e3769dc'): {
                None: FileStatusExtension.COMPILE_ERROR
            },
            ShortCommitHash('2e654f9963'): {
                None: FileStatusExtension.BLOCKED
            }
        }, {
            ShortCommitHash('9872ba420c'): {
                None: FileStatusExtension.SUCCESS
            }
        }])

        PCM.get_status(
            self.case_study, MockExperimentMultiReport, 5, False, False, True,
            total_status_occurrences
        )
        status = PCM.get_total_status(total_status_occurrences, 15, True)
        self.assertEqual(
            status,
            """--------------------------------------------------------------------------------
Total:         (  1/16) processed [1/1/1/1/1/10/1]"""
        )

        mock_get_tagged_experiment_specific_revisions.assert_called()

        # Care: The second block is duplicated to check if we prevent
        # adding the same revisions twice

        mock_get_tagged_experiment_specific_revisions.reset_mock()

        PCM.get_status(
            self.case_study, MockExperimentMultiReport, 5, False, False, True,
            total_status_occurrences
        )
        status = PCM.get_total_status(total_status_occurrences, 15, True)
        self.assertEqual(
            status,
            """--------------------------------------------------------------------------------
Total:         (  1/16) processed [1/1/1/1/1/10/1]"""
        )

        mock_get_tagged_experiment_specific_revisions.assert_called()
