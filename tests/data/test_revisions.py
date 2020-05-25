"""Test revision helper functions."""

import unittest
import unittest.mock as mock

from varats.data.revisions import filter_blocked_revisions
from varats.projects.c_projects.glibc import Glibc
from varats.projects.c_projects.gravity import Gravity


class TestFilterBlockedRevisions(unittest.TestCase):
    """Test if the revision filter function correctly filters revision lists."""

    def setUp(self) -> None:
        gravity_patcher = mock.patch(
            'varats.projects.c_projects.gravity.Gravity', spec=Gravity
        )
        self.addCleanup(gravity_patcher.stop)
        self.mock_gravity = gravity_patcher.start()
        self.blocked_revision = ['e207f0cc87', '109a1e6233']
        self.mock_gravity.is_blocked_revision = lambda x: (
            x in self.blocked_revision, ""
        )

    def test_filter_empty_list(self):
        self.assertListEqual([], filter_blocked_revisions([],
                                                          self.mock_gravity))

    def test_filter_list_without_blocked(self):
        """Checks if we do not filter unblocked revisions."""
        unblocked_revisions = [
            '8bece6fd0c', 'fcfadde2a5', 'd6306bc0d5', '2dc8bdd988', 'a6158db8bb'
        ]

        filtered_revisions = filter_blocked_revisions(
            unblocked_revisions, self.mock_gravity
        )

        self.assertLessEqual(unblocked_revisions, filtered_revisions)

    def test_filter_list_with_blocked(self):
        """Checks if we filter blocked revisions."""
        unblocked_revisions = [
            '8bece6fd0c', 'fcfadde2a5', 'd6306bc0d5', '2dc8bdd988', 'a6158db8bb'
        ]
        blocked_revision = ['e207f0cc87', '109a1e6233']

        filtered_revisions = filter_blocked_revisions(
            unblocked_revisions + blocked_revision, self.mock_gravity
        )

        self.assertLessEqual(unblocked_revisions, filtered_revisions)

    def test_filter_list_of_non_blocked_project(self):
        """Checks if the filter works on projects that don't have blocked
        revisions."""
        unblocked_revisions = ['61416e1921', '16536e98e3']

        filtered_revisions = filter_blocked_revisions(
            unblocked_revisions, Glibc
        )

        self.assertLessEqual(unblocked_revisions, filtered_revisions)
