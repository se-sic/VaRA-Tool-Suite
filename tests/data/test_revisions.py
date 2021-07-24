"""Test revision helper functions."""

import unittest
import unittest.mock as mock

from benchbuild.utils.revision_ranges import block_revisions, SingleRevision

from tests.test_utils import DummyGit
from varats.projects.c_projects.glibc import Glibc
from varats.projects.c_projects.gravity import Gravity
from varats.revision.revisions import filter_blocked_revisions
from varats.utils.git_util import ShortCommitHash


class TestFilterBlockedRevisions(unittest.TestCase):
    """Test if the revision filter function correctly filters revision lists."""

    def setUp(self) -> None:
        self.blocked_revision = ['e207f0cc87', '109a1e6233']
        mocked_gravity_source = block_revisions([
            SingleRevision(rev) for rev in self.blocked_revision
        ])(DummyGit(remote="/dev/null", local="/dev/null"))
        project_source_patcher = mock.patch(
            'varats.revision.revisions.get_primary_project_source'
        )
        self.addCleanup(project_source_patcher.stop)
        project_source_patcher.start().return_value = mocked_gravity_source

    def test_filter_empty_list(self):
        self.assertListEqual([], filter_blocked_revisions([], Gravity))

    def test_filter_list_without_blocked(self):
        """Checks if we do not filter unblocked revisions."""
        unblocked_revisions = list(
            map(
                ShortCommitHash, [
                    '8bece6fd0c', 'fcfadde2a5', 'd6306bc0d5', '2dc8bdd988',
                    'a6158db8bb'
                ]
            )
        )

        filtered_revisions = filter_blocked_revisions(
            unblocked_revisions, Gravity
        )

        self.assertLessEqual(unblocked_revisions, filtered_revisions)

    def test_filter_list_with_blocked(self):
        """Checks if we filter blocked revisions."""
        unblocked_revisions = list(
            map(
                ShortCommitHash, [
                    '8bece6fd0c', 'fcfadde2a5', 'd6306bc0d5', '2dc8bdd988',
                    'a6158db8bb'
                ]
            )
        )
        blocked_revision = list(
            map(ShortCommitHash, ['e207f0cc87', '109a1e6233'])
        )

        filtered_revisions = filter_blocked_revisions(
            unblocked_revisions + blocked_revision, Gravity
        )

        self.assertLessEqual(unblocked_revisions, filtered_revisions)

    def test_filter_list_of_non_blocked_project(self):
        """Checks if the filter works on projects that don't have blocked
        revisions."""
        unblocked_revisions = list(
            map(ShortCommitHash, ['61416e1921', '16536e98e3'])
        )

        filtered_revisions = filter_blocked_revisions(
            unblocked_revisions, Glibc
        )

        self.assertLessEqual(unblocked_revisions, filtered_revisions)
