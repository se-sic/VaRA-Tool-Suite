"""Test bug_provider and bug modules."""
import unittest
from unittest.mock import Mock

from varats.provider.bug.bug import _has_closed_a_bug


class TestBugDetectionStrategies(unittest.TestCase):
    """Test several parts of the bug detection strategies used by the
    BugProvider."""

    def test_issue_events_closing_bug(self):
        """Test identifying issue events that close a bug related issue, with
        and without associated commit id."""

        # mock issue with correct labels
        bug_label = Mock(**{'name.return_value': "bug"})
        irrelevant_label = Mock(**{'name.return_value': "good first issue"})
        issue = Mock(
            **{
                'labels.return_value': [irrelevant_label, bug_label],
                'id.return_value': 1
            }
        )

        # sane mock issue event
        issue_event_bug = Mock(
            **{
                'event.return_value': "closed",
                'commit_id.return_value': "1234",
                'issue.return_value': issue
            }
        )

        # mock issue event without corresponding commit
        issue_event_no_commit = Mock(
            **{
                'event.return_value': "closed",
                'commit_id.return_value': None,
                'issue.return_value': issue
            }
        )

        # check if Issues get identified correctly
        self.assertTrue(_has_closed_a_bug(issue_event_bug))
        self.assertFalse(_has_closed_a_bug(issue_event_no_commit))

    def test_issue_events_closing_no_bug(self):
        """Test identifying issue events closing an issue that is not a bug."""

        # mock issue without labels
        issue = Mock(**{'labels.return_value': [], 'id.return_value': 2})

        issue_event = Mock(
            **{
                'event.return_value': "closed",
                'commit_id.return_value': "1235",
                'issue.return_value': issue
            }
        )

        self.assertFalse(_has_closed_a_bug(issue_event))

    def test_issue_events_not_closing(self):
        """Test identifying issue events not closing their issue."""

        # issue representing bug
        bug_label = Mock(**{'name.return_value': "bug"})
        issue = Mock(
            **{
                'labels.return_value': [bug_label],
                'id.return_value': 3
            }
        )

        issue_event_pinned = Mock(
            **{
                'event.return_value': "pinned",
                'commit_id.return_value': None,
                'issue.return_value': issue
            }
        )
        issue_event_assigned = Mock(
            **{
                'event.return_value': "assigned",
                'commit_id.return_value': "1236",
                'issue.return_value': issue
            }
        )

        self.assertFalse(_has_closed_a_bug(issue_event_pinned))
        self.assertFalse(_has_closed_a_bug(issue_event_assigned))
