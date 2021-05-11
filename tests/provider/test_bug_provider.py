"""Test bug_provider and bug modules."""
import datetime
import typing as tp
import unittest
from unittest.mock import create_autospec, patch, MagicMock

import pygit2
from github.Issue import Issue
from github.IssueEvent import IssueEvent
from github.Label import Label
from pydriller import git as pydrepo

from varats.projects.test_projects.bug_provider_test_repos import (
    BasicBugDetectionTestRepo,
)
from varats.provider.bug.bug import (
    _has_closed_a_bug,
    _is_closing_message,
    _create_corresponding_pygit_bug,
    _filter_all_issue_pygit_bugs,
    _filter_all_commit_message_pygit_bugs,
    PygitSuspectTuple,
)
from varats.provider.bug.bug_provider import BugProvider


class DummyIssueData:
    """Dummy Issue Tracking data for Issue Bug Tests."""
    __bug_label = create_autospec(Label)
    __bug_label.name = "bug"

    __issue_firstbug = create_autospec(Issue)
    __issue_firstbug.number = 5
    __issue_firstbug.labels = [__bug_label]
    __issue_firstbug.created_at = datetime.datetime(2020, 4, 20, 13, 37)

    __issue_nobug = create_autospec(Issue)
    __issue_nobug.number = 6
    __issue_nobug.labels = []
    __issue_nobug.created_at = datetime.datetime(2020, 4, 21, 13, 40)

    __issue_secondbug = create_autospec(Issue)
    __issue_secondbug.number = 7
    __issue_secondbug.labels = [__bug_label]
    __issue_secondbug.created_at = datetime.datetime(2020, 4, 22, 7, 52)

    @staticmethod
    def issue_firstbug() -> MagicMock:
        return DummyIssueData.__issue_firstbug

    @staticmethod
    def issue_nobug() -> MagicMock:
        return DummyIssueData.__issue_nobug

    @staticmethod
    def issue_secondbug() -> MagicMock:
        return DummyIssueData.__issue_secondbug


class DummyPydrillerRepo(pydrepo.Git):
    """Dummy pydriller repo class that overrides basic functionality."""

    # pydriller history (for issue event tests)
    # no suspect, weak suspect for first bug
    __intro_secondbug_pre_report = create_autospec(pydrepo.Commit)
    __intro_secondbug_pre_report.hash = "1239i1"
    __intro_secondbug_pre_report.committer_date = datetime.datetime(
        2020, 4, 21, 13, 13
    )
    # second bug fix is also partial fix for first bug
    __fix_secondbug = create_autospec(pydrepo.Commit)
    __fix_secondbug.hash = "1239"
    __fix_secondbug.committer_date = datetime.datetime(2020, 4, 22, 16, 2)

    # hard suspect for first bug
    __intro_firstbug_post_hard = create_autospec(pydrepo.Commit)
    __intro_firstbug_post_hard.hash = "1240i1"
    __intro_firstbug_post_hard.committer_date = datetime.datetime(
        2020, 4, 20, 19, 34
    )

    # first bug fix
    __fix_firstbug = create_autospec(pydrepo.Commit)
    __fix_firstbug.hash = "1240"
    __fix_firstbug.committer_date = datetime.datetime(2020, 4, 23, 5, 23)

    __important_commits = {
        __intro_secondbug_pre_report, __intro_firstbug_post_hard,
        __fix_firstbug, __fix_secondbug
    }

    def __init__(self, _path):
        pass

    @staticmethod
    def fix_firstbug() -> MagicMock:
        return DummyPydrillerRepo.__fix_firstbug

    @staticmethod
    def fix_secondbug() -> MagicMock:
        return DummyPydrillerRepo.__fix_secondbug

    @staticmethod
    def intro_firstbug() -> MagicMock:
        return DummyPydrillerRepo.__intro_firstbug_post_hard

    @staticmethod
    def intro_secondbug() -> MagicMock:
        return DummyPydrillerRepo.__intro_secondbug_pre_report

    def get_commit(self, commit_id: str) -> MagicMock:
        """Method that creates pydriller Commit mocks for given ID."""
        for important_commit in DummyPydrillerRepo.__important_commits:
            if commit_id == important_commit.hash:
                return important_commit

        # create new mocks for not already predetermined commits
        mock_commit = create_autospec(pydrepo.Commit)
        mock_commit.hash = commit_id
        mock_commit.committer_date = datetime.datetime.now()
        return mock_commit

    def get_commits_last_modified_lines(
        self,
        commit: pydrepo.Commit,
        modification: pydrepo.ModifiedFile = None,
        hashes_to_ignore_path: str = None
    ) -> tp.Dict[str, tp.Set[str]]:
        """Method that returns corresponding introducing ids."""
        if commit.hash == DummyPydrillerRepo.__fix_firstbug.hash:
            return {
                "important line": {
                    DummyPydrillerRepo.__fix_secondbug.hash,
                    DummyPydrillerRepo.__intro_secondbug_pre_report.hash,
                    DummyPydrillerRepo.__intro_firstbug_post_hard.hash
                }
            }
        if commit.hash == DummyPydrillerRepo.__fix_secondbug.hash:
            return {
                "important line": {
                    DummyPydrillerRepo.__intro_secondbug_pre_report.hash
                }
            }
        return {}


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

        with patch('varats.provider.bug.bug.pydrepo.Git', DummyPydrillerRepo):
            pybug = _create_corresponding_pygit_bug(
                issue_event.commit_id, self.mock_repo, issue_event.issue.number
            )

            self.assertEqual(issue_event.commit_id, pybug.fixing_commit.hex)
            self.assertEqual(issue_event.issue.number, pybug.issue_id)

    def test_filter_issue_bugs(self):
        """Test on a set of IssueEvents whether the corresponding set of bugs is
        created correctly."""

        event_close_first_nocommit = create_autospec(IssueEvent)
        event_close_first_nocommit.event = "closed"
        event_close_first_nocommit.commit_id = None
        event_close_first_nocommit.issue = DummyIssueData.issue_firstbug()

        event_close_no_bug = create_autospec(IssueEvent)
        event_close_no_bug.event = "closed"
        event_close_no_bug.commit_id = "1238"
        event_close_no_bug.issue = DummyIssueData.issue_nobug()

        event_reopen_first = create_autospec(IssueEvent)
        event_reopen_first.event = "reopened"
        event_reopen_first.commit_id = None
        event_reopen_first.issue = DummyIssueData.issue_firstbug()

        event_close_second = create_autospec(IssueEvent)
        event_close_second.event = "closed"
        event_close_second.commit_id = DummyPydrillerRepo.fix_secondbug().hash
        event_close_second.issue = DummyIssueData.issue_secondbug()

        event_close_first = create_autospec(IssueEvent)
        event_close_first.event = "closed"
        event_close_first.commit_id = DummyPydrillerRepo.fix_firstbug().hash
        event_close_first.issue = DummyIssueData.issue_firstbug()

        def mock_get_all_issue_events(_project_name: str):
            return iter([
                event_close_first_nocommit, event_close_no_bug,
                event_reopen_first, event_close_second, event_close_first
            ])

        def mock_get_repo(_project_name: str):
            return self.mock_repo

        with patch(
                'varats.provider.bug.bug._get_all_issue_events',
                mock_get_all_issue_events),\
            patch(
                'varats.provider.bug.bug.get_local_project_git',
                mock_get_repo),\
            patch(
                'varats.provider.bug.bug.pydrepo.Git',
                DummyPydrillerRepo):

            # issue filter method for pygit bugs
            def accept_pybugs(sus_tuple: PygitSuspectTuple):
                return sus_tuple.create_corresponding_bug()

            # create set of fixing IDs of found bugs
            pybugs = _filter_all_issue_pygit_bugs("", accept_pybugs)
            pybug_fix_ids = set(pybug.fixing_commit.hex for pybug in pybugs)
            expected_fix_ids = {"1239", "1240"}

            intro_first_bug = set()
            intro_second_bug = set()
            for pybug in pybugs:
                if pybug.fixing_commit.hex == event_close_second.commit_id:
                    intro_second_bug = {
                        intro_commit.hex
                        for intro_commit in pybug.introducing_commits
                    }
                if pybug.fixing_commit.hex == event_close_first.commit_id:
                    intro_first_bug = {
                        intro_commit.hex
                        for intro_commit in pybug.introducing_commits
                    }

            expected_first_bug_intro_ids = {"1239i1", "1239"}
            expected_second_bug_intro_ids = {"1239i1"}

            self.assertEqual(expected_fix_ids, pybug_fix_ids)
            self.assertEqual(expected_first_bug_intro_ids, intro_first_bug)
            self.assertEqual(expected_second_bug_intro_ids, intro_second_bug)

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

        def mock_walk(_start_id: str, _sort_mode: int):
            return iter([
                first_fixing_commit, first_non_fixing_commit,
                second_non_fixing_commit, second_fixing_commit
            ])

        # customize walk method of mock repo
        self.mock_repo.walk = create_autospec(
            pygit2.Repository.walk, side_effect=mock_walk
        )

        def mock_get_repo(_project_name: str):
            return self.mock_repo

        with patch(
                'varats.provider.bug.bug.get_local_project_git',
                mock_get_repo),\
            patch(
                'varats.provider.bug.bug.pydrepo.Git',
                DummyPydrillerRepo):

            # commit filter method for pygit bugs
            def accept_pybugs(commit: pygit2.Commit):
                if _is_closing_message(commit.message):
                    return _create_corresponding_pygit_bug(
                        commit.hex, self.mock_repo
                    )
                return None

            pybug_ids = set(
                pybug.fixing_commit.hex for pybug in
                _filter_all_commit_message_pygit_bugs("", accept_pybugs)
            )
            expected_ids = {"1241", "1244"}

            self.assertEqual(expected_ids, pybug_ids)


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

        pybugs = provider.find_all_pygit_bugs()

        pybug_fix_ids = set(pybug.fixing_commit.hex for pybug in pybugs)
        pybug_fix_msgs = set(pybug.fixing_commit.message for pybug in pybugs)

        # asserting correct fixes have been found
        self.assertEqual(pybug_fix_ids, self.basic_expected_fixes)
        self.assertEqual(pybug_fix_msgs, self.basic_expected_msgs)

        # find certain pybugs searching them by their fixing hashes
        pybug_first = provider.find_pygit_bug_by_fix(
            "ddf0ba95408dc5508504c84e6616c49128410389"
        )
        pybug_first_intro_ids = set(
            intro_commit.hex
            for intro_commit in next(iter(pybug_first)).introducing_commits
        )

        pybug_second = provider.find_pygit_bug_by_fix(
            "d846bdbe45e4d64a34115f5285079e1b5f84007f"
        )
        pybug_second_intro_ids = set(
            intro_commit.hex
            for intro_commit in next(iter(pybug_second)).introducing_commits
        )

        pybug_third = provider.find_pygit_bug_by_fix(
            "2da78b2820370f6759e9086fad74155d6655e93b"
        )
        pybug_third_intro_ids = set(
            intro_commit.hex
            for intro_commit in next(iter(pybug_third)).introducing_commits
        )

        pybug_fourth = provider.find_pygit_bug_by_fix(
            "3b76c8d295385358375fefdb0cf045d97ad2d193"
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

        rawbugs = provider.find_all_raw_bugs()

        rawbug_fix_ids = set(rawbug.fixing_commit for rawbug in rawbugs)

        # asserting correct fixes have been found
        self.assertEqual(rawbug_fix_ids, self.basic_expected_fixes)

        # find certain rawbugs searching them by their fixing hashes
        rawbug_first = provider.find_raw_bug_by_fix(
            "ddf0ba95408dc5508504c84e6616c49128410389"
        )
        rawbug_first_intro_ids = next(iter(rawbug_first)).introducing_commits

        rawbug_second = provider.find_raw_bug_by_fix(
            "d846bdbe45e4d64a34115f5285079e1b5f84007f"
        )
        rawbug_second_intro_ids = next(iter(rawbug_second)).introducing_commits

        rawbug_third = provider.find_raw_bug_by_fix(
            "2da78b2820370f6759e9086fad74155d6655e93b"
        )
        rawbug_third_intro_ids = next(iter(rawbug_third)).introducing_commits

        rawbug_fourth = provider.find_raw_bug_by_fix(
            "3b76c8d295385358375fefdb0cf045d97ad2d193"
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
