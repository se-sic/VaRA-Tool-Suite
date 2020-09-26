"""Test bug_provider and bug modules."""
import unittest
from unittest.mock import Mock, create_autospec

from github.Issue import Issue
from github.IssueEvent import IssueEvent
from github.Label import Label

from varats.provider.bug.bug import _has_closed_a_bug


class TestBugDetectionStrategies(unittest.TestCase):
    """Test several parts of the bug detection strategies used by the
    BugProvider."""

    def test_issue_events_closing_bug(self):
        """Test identifying issue events that close a bug related issue, with
        and without associated commit id."""

        # mock issue with correct labels
        bug_label = create_autospec(Label)
        bug_label.name = "bug"
        irrelevant_label = create_autospec(Label)
        irrelevant_label.name = "good first issue"

        issue = create_autospec(Issue)
        issue.id = 1
        issue.labels = [irrelevant_label, bug_label]

        # sane mock issue event
        issue_event_bug = create_autospec(IssueEvent)
        issue_event_bug.event = "closed"
        issue_event_bug.commit_id = "1234"
        issue_event_bug.issue = issue

        # mock issue event without corresponding commit
        issue_event_no_commit = create_autospec(IssueEvent)
        issue_event_no_commit.event = "closed"
        issue_event_no_commit.commit_id = None
        issue_event_no_commit.issue = issue

        # check if Issues get identified correctly
        self.assertTrue(_has_closed_a_bug(issue_event_bug))
        self.assertFalse(_has_closed_a_bug(issue_event_no_commit))

    def test_issue_events_closing_no_bug(self):
        """Test identifying issue events closing an issue that is not a bug."""

        # mock issue without labels
        issue = create_autospec(Issue)
        issue.id = 2
        issue.labels = []

        issue_event = create_autospec(IssueEvent)
        issue_event.event = "closed"
        issue_event.commit_id = "1235"
        issue_event.issue = issue

        self.assertFalse(_has_closed_a_bug(issue_event))

    def test_issue_events_not_closing(self):
        """Test identifying issue events not closing their issue."""

        # issue representing bug
        bug_label = create_autospec(Label)
        bug_label.name = "bug"

        issue = create_autospec(Issue)
        issue.id = 3
        issue.labels = [bug_label]

        issue_event_pinned = create_autospec(IssueEvent)
        issue_event_pinned.event = "pinned"
        issue_event_pinned.commit_id = None
        issue_event_pinned.issue = issue

        issue_event_assigned = create_autospec(IssueEvent)
        issue_event_assigned.event = "assigned"
        issue_event_assigned.commit_id = "1236"
        issue_event_assigned.issue = issue

        self.assertFalse(_has_closed_a_bug(issue_event_pinned))
        self.assertFalse(_has_closed_a_bug(issue_event_assigned))
