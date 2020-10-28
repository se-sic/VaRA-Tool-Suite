"""Test bug_provider and bug modules."""
import unittest
from unittest.mock import create_autospec, patch

import pygit2
from github.Issue import Issue
from github.IssueEvent import IssueEvent
from github.Label import Label

from varats.provider.bug.bug import (
    _has_closed_a_bug,
    _is_closing_message,
    _create_corresponding_pygit_bug,
    _create_corresponding_raw_bug,
    _filter_all_issue_raw_bugs,
    _filter_all_issue_pygit_bugs,
    _filter_all_commit_message_raw_bugs,
    _filter_all_commit_message_pygit_bugs,
)


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

    def test_pygit_bug_creation(self):
        """Test whether created pygit bug objects fit their corresponding
        issue."""

        # issue representing a bug
        bug_label = create_autospec(Label)
        bug_label.name = "bug"

        issue = create_autospec(Issue)
        issue.number = 4
        issue.labels = [bug_label]

        issue_event = create_autospec(IssueEvent)
        issue_event.event = "closed"
        issue_event.commit_id = "1237"
        issue_event.issue = issue

        # associated commit mock
        issue_commit = create_autospec(pygit2.Commit)
        issue_commit.hex = "1237"

        mock_repo = create_autospec(pygit2.Repository)
        mock_repo.revparse_single = create_autospec(
            pygit2.Repository.revparse_single, return_value=issue_commit
        )

        pybug = _create_corresponding_pygit_bug(
            issue_event.commit_id, mock_repo, issue_event.issue.number
        )

        self.assertEqual(pybug.fixing_commit.hex, issue_event.commit_id)
        self.assertEqual(pybug.issue_id, issue_event.issue.number)

    def test_filter_issue_bugs(self):
        """Test on a set of IssueEvents whether the corresponding set of bugs is
        created correctly."""

        bug_label = create_autospec(Label)
        bug_label.name = "bug"

        issue_firstbug = create_autospec(Issue)
        issue_firstbug.number = 5
        issue_firstbug.labels = [bug_label]

        issue_nobug = create_autospec(Issue)
        issue_nobug.number = 6
        issue_nobug.labels = []

        issue_secondbug = create_autospec(Issue)
        issue_secondbug.number = 7
        issue_secondbug.labels = [bug_label]

        event_close_first_nocommit = create_autospec(IssueEvent)
        event_close_first_nocommit.event = "closed"
        event_close_first_nocommit.commit_id = None
        event_close_first_nocommit.issue = issue_firstbug

        event_close_no_bug = create_autospec(IssueEvent)
        event_close_no_bug.event = "closed"
        event_close_no_bug.commit_id = "1238"
        event_close_no_bug.issue = issue_nobug

        event_reopen_first = create_autospec(IssueEvent)
        event_reopen_first.event = "reopened"
        event_reopen_first.commit_id = None
        event_reopen_first.issue = issue_firstbug

        event_close_second = create_autospec(IssueEvent)
        event_close_second.event = "closed"
        event_close_second.commit_id = "1239"
        event_close_second.issue = issue_secondbug

        event_close_first = create_autospec(IssueEvent)
        event_close_first.event = "closed"
        event_close_first.commit_id = "1240"
        event_close_first.issue = issue_firstbug

        # Method that creates simple pygit2 Commit mocks for given ID
        def mock_revparse(commit_id: str):
            mock_commit = create_autospec(pygit2.Commit)
            mock_commit.hex = commit_id
            return mock_commit

        mock_repo = create_autospec(pygit2.Repository)
        mock_repo.revparse_single = create_autospec(
            pygit2.Repository.revparse_single, side_effect=mock_revparse
        )

        def mock_get_all_issue_events(_project_name: str):
            return iter([
                event_close_first_nocommit, event_close_no_bug,
                event_reopen_first, event_close_second, event_close_first
            ])

        def mock_get_repo(_project_name: str):
            return mock_repo

        with patch(
                'varats.provider.bug.bug._get_all_issue_events',
                mock_get_all_issue_events),\
            patch(
                'varats.provider.bug.bug.get_local_project_git',
                mock_get_repo):

            # issue filter method for pygit bugs
            def accept_pybugs(event: IssueEvent):
                if _has_closed_a_bug(event) and event.commit_id:
                    return _create_corresponding_pygit_bug(
                        event.commit_id, mock_repo, event.issue.number
                    )
                return None

            # issue filter method for raw bugs
            def accept_rawbugs(event: IssueEvent):
                if _has_closed_a_bug(event) and event.commit_id:
                    return _create_corresponding_raw_bug(
                        event.commit_id, mock_repo, event.issue.number
                    )
                return None

            # create set of fixing IDs of found bugs
            pybug_ids = set(
                pybug.fixing_commit.hex
                for pybug in _filter_all_issue_pygit_bugs("", accept_pybugs)
            )
            rawbug_ids = set(
                rawbug.fixing_commit
                for rawbug in _filter_all_issue_raw_bugs("", accept_rawbugs)
            )
            expected_ids = {"1239", "1240"}

            self.assertEqual(pybug_ids, expected_ids)
            self.assertEqual(rawbug_ids, expected_ids)

    def test_filter_commit_message_bugs(self):
        """Test on the commit history of a project whether the corresponding set
        of bugs is created correctly."""

        first_fixing_commit = create_autospec(pygit2.Commit)
        first_fixing_commit.hex = "1241"
        first_fixing_commit.message = "Fixed first issue"

        first_non_fixing_commit = create_autospec(pygit2.Commit)
        first_non_fixing_commit.hex = "1242"
        first_non_fixing_commit.message = "Added documentation\n" + \
                                          "Grammar Errors need to be fixed"

        second_non_fixing_commit = create_autospec(pygit2.Commit)
        second_non_fixing_commit.hex = "1243"
        second_non_fixing_commit.message = "Added feature X"

        second_fixing_commit = create_autospec(pygit2.Commit)
        second_fixing_commit.hex = "1244"
        second_fixing_commit.message = "fixes second problem"

        # Method that creates simple pygit2 Commit mocks for given ID
        def mock_revparse(commit_id: str):
            mock_commit = create_autospec(pygit2.Commit)
            mock_commit.hex = commit_id
            return mock_commit

        def mock_walk(_start_id: str, _sort_mode: int):
            return iter([
                first_fixing_commit, first_non_fixing_commit,
                second_non_fixing_commit, second_fixing_commit
            ])

        mock_repo = create_autospec(pygit2.Repository)
        mock_repo.revparse_single = create_autospec(
            pygit2.Repository.revparse_single, side_effect=mock_revparse
        )
        mock_repo.walk = create_autospec(
            pygit2.Repository.walk, side_effect=mock_walk
        )

        def mock_get_repo(_project_name: str):
            return mock_repo

        with patch(
            'varats.provider.bug.bug.get_local_project_git', mock_get_repo
        ):

            # commit filter method for pygit bugs
            def accept_pybugs(commit: pygit2.Commit):
                if _is_closing_message(commit.message):
                    return _create_corresponding_pygit_bug(
                        commit.hex, mock_repo
                    )
                return None

            # commit filter method for raw bugs
            def accept_rawbugs(commit: pygit2.Commit):
                if _is_closing_message(commit.message):
                    return _create_corresponding_raw_bug(commit.hex, mock_repo)
                return None

            pybug_ids = set(
                pybug.fixing_commit.hex for pybug in
                _filter_all_commit_message_pygit_bugs("", accept_pybugs)
            )
            rawbug_ids = set(
                rawbug.fixing_commit for rawbug in
                _filter_all_commit_message_raw_bugs("", accept_rawbugs)
            )
            expected_ids = {"1241", "1244"}

            self.assertEqual(pybug_ids, expected_ids)
            self.assertEqual(rawbug_ids, expected_ids)
