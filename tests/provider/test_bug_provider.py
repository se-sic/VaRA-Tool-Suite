"""Test bug_provider and bug modules."""
import unittest
from unittest.mock import create_autospec

import pygit2
from github.Issue import Issue
from github.IssueEvent import IssueEvent
from github.Label import Label

from varats.projects.test_projects.bug_provider_test_repos import (
    BasicBugDetectionTestRepo,
)
from varats.provider.bug.bug import _has_closed_a_bug
from varats.provider.bug.bug_provider import BugProvider


class TestBugDetectionStrategies(unittest.TestCase):
    """Test several parts of the bug detection strategies used by the
    BugProvider."""

    def setUp(self) -> None:
        """Set up repo dummy objects needed for multiple tests."""

        def mock_revparse(commit_id: str):
            """Method that creates simple pygit2 Commit mocks for given ID."""
            mock_commit = create_autospec(pygit2.Commit)
            mock_commit.hex = commit_id
            return mock_commit

        # pygit2 dummy repo
        self.mock_repo = create_autospec(pygit2.Repository)
        self.mock_repo.revparse_single = create_autospec(
            pygit2.Repository.revparse_single, side_effect=mock_revparse
        )

    def test_issue_events_closing_bug(self):
        """Test identifying issue events that close a bug related issue, with
        and without associated commit id."""

        # mock issue with correct labels
        bug_label = create_autospec(Label)
        bug_label.name = "bug"
        irrelevant_label = create_autospec(Label)
        irrelevant_label.name = "good first issue"

        issue = create_autospec(Issue)
        issue.number = 1
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
        issue.number = 2
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
        issue.number = 3
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


class TestBugProvider(unittest.TestCase):
    """Test the bug provider on test projects from vara-test-repos."""

    def setUp(self) -> None:
        """Set up expected data for respective test repos."""
        self.basic_expected_fixes = {
            "ddf0ba95408dc5508504c84e6616c49128410389",
            "d846bdbe45e4d64a34115f5285079e1b5f84007f",
            "2da78b2820370f6759e9086fad74155d6655e93b",
            "3b76c8d295385358375fefdb0cf045d97ad2d193"
        }
        self.basic_expected_msgs = {
            "Fixed function arguments\n", "Fixes answer to everything\n",
            "Fixes return type of multiply\n", "Multiplication result fix\n"
        }
        self.basic_expected_first_introduction = {
            "343bea18b421cfa2eb5945b2672f62f171abcc83"
        }
        self.basic_expected_second_introduction = {
            "ddf0ba95408dc5508504c84e6616c49128410389"
        }
        self.basic_expected_third_introduction = {
            "8fae311154a28b7928fe667b6aad09319259b1aa"
        }
        self.basic_expected_fourth_introduction = {
            "c4b7bd9a2cedf1eb67d13be3cf4e826273cfe17b"
        }

    def test_basic_repo_pygit_bugs(self):
        """Test provider on basic_bug_detection_test_repo."""
        provider = BugProvider.get_provider_for_project(
            BasicBugDetectionTestRepo
        )

        pybugs = provider.find_pygit_bugs()

        pybug_fix_ids = set(str(pybug.fixing_commit.id) for pybug in pybugs)
        pybug_fix_msgs = set(pybug.fixing_commit.message for pybug in pybugs)

        # asserting correct fixes have been found
        self.assertEqual(pybug_fix_ids, self.basic_expected_fixes)
        self.assertEqual(pybug_fix_msgs, self.basic_expected_msgs)

        # find certain pybugs searching them by their fixing hashes
        pybug_first = provider.find_pygit_bugs(
            fixing_commit="ddf0ba95408dc5508504c84e6616c49128410389"
        )
        pybug_first_intro_ids = set(
            intro_commit.hex
            for intro_commit in next(iter(pybug_first)).introducing_commits
        )

        pybug_second = provider.find_pygit_bugs(
            fixing_commit="d846bdbe45e4d64a34115f5285079e1b5f84007f"
        )
        pybug_second_intro_ids = set(
            intro_commit.hex
            for intro_commit in next(iter(pybug_second)).introducing_commits
        )

        pybug_third = provider.find_pygit_bugs(
            fixing_commit="2da78b2820370f6759e9086fad74155d6655e93b"
        )
        pybug_third_intro_ids = set(
            intro_commit.hex
            for intro_commit in next(iter(pybug_third)).introducing_commits
        )

        pybug_fourth = provider.find_pygit_bugs(
            fixing_commit="3b76c8d295385358375fefdb0cf045d97ad2d193"
        )
        pybug_fourth_intro_ids = set(
            intro_commit.hex
            for intro_commit in next(iter(pybug_fourth)).introducing_commits
        )

        self.assertEqual(
            self.basic_expected_first_introduction, pybug_first_intro_ids
        )
        self.assertEqual(
            self.basic_expected_second_introduction, pybug_second_intro_ids
        )
        self.assertEqual(
            self.basic_expected_third_introduction, pybug_third_intro_ids
        )
        self.assertEqual(
            self.basic_expected_fourth_introduction, pybug_fourth_intro_ids
        )

    def test_basic_repo_raw_bugs(self):
        """Test provider on basic_bug_detection_test_repo."""
        provider = BugProvider.get_provider_for_project(
            BasicBugDetectionTestRepo
        )

        rawbugs = provider.find_raw_bugs()

        rawbug_fix_ids = set(rawbug.fixing_commit for rawbug in rawbugs)

        # asserting correct fixes have been found
        self.assertEqual(rawbug_fix_ids, self.basic_expected_fixes)

        # find certain rawbugs searching them by their fixing hashes
        rawbug_first = provider.find_raw_bugs(
            fixing_commit="ddf0ba95408dc5508504c84e6616c49128410389"
        )
        rawbug_first_intro_ids = next(iter(rawbug_first)).introducing_commits

        rawbug_second = provider.find_raw_bugs(
            fixing_commit="d846bdbe45e4d64a34115f5285079e1b5f84007f"
        )
        rawbug_second_intro_ids = next(iter(rawbug_second)).introducing_commits

        rawbug_third = provider.find_raw_bugs(
            fixing_commit="2da78b2820370f6759e9086fad74155d6655e93b"
        )
        rawbug_third_intro_ids = next(iter(rawbug_third)).introducing_commits

        rawbug_fourth = provider.find_raw_bugs(
            fixing_commit="3b76c8d295385358375fefdb0cf045d97ad2d193"
        )
        rawbug_fourth_intro_ids = next(iter(rawbug_fourth)).introducing_commits

        self.assertEqual(
            self.basic_expected_first_introduction, rawbug_first_intro_ids
        )
        self.assertEqual(
            self.basic_expected_second_introduction, rawbug_second_intro_ids
        )
        self.assertEqual(
            self.basic_expected_third_introduction, rawbug_third_intro_ids
        )
        self.assertEqual(
            self.basic_expected_fourth_introduction, rawbug_fourth_intro_ids
        )
