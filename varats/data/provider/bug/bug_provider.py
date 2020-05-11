"""
Module for the :class:`BugProvider`.
"""
import logging
import re
import typing as tp
from collections import defaultdict

from benchbuild.project import Project
from github import Github
from github.IssueEvent import IssueEvent
from github.PaginatedList import PaginatedList
from github.Repository import Repository

from varats.data.provider.provider import Provider
from varats.utils.github_util import get_cached_github_object

LOG = logging.getLogger(__name__)

GITHUB_URL_PATTERN = re.compile(r"https://github\.com/(.*)/(.*)\.git")


class BugProvider(Provider):
    """
    Provides bug information for a project.
    """

    def __init__(self, project: tp.Type[Project],
                 github_project_name: tp.Optional[str]) -> None:
        super().__init__(project)
        self.__github_project_name = github_project_name

    @classmethod
    def create_provider_for_project(
            cls, project: tp.Type[Project]) -> tp.Optional['BugProvider']:
        match = GITHUB_URL_PATTERN.match(project.repository)
        if match:
            return BugProvider(project, f"{match.group(1)}/{match.group(2)}")
        return None

    @classmethod
    def create_default_provider(cls,
                                project: tp.Type[Project]) -> 'BugProvider':
        return BugDefaultProvider(project)

    def get_resolved_bugs(self) -> tp.Dict[str, tp.Set[str]]:
        """
        Get all bugs associated with this provider's project along with the
        fixing commit.

        Return:
            a set of tuples of commit hash and bug ids
        """
        if self.__github_project_name:
            return get_github_bugs(self.__github_project_name)
        return {}


class BugDefaultProvider(BugProvider):
    """
    Default implementation of the :class:`Bug provider` for projects that
    do not (yet) support bugs.
    """

    def __init__(self, project: tp.Type[Project]) -> None:
        # pylint: disable=E1003
        super(BugProvider, self).__init__(project)

    def get_resolved_bugs(self) -> tp.Dict[str, tp.Set[str]]:
        return {}


def get_github_bugs(full_repo_name: str) -> tp.Dict[str, tp.Set[str]]:
    """
    Retrieves bugs from github by searching issues that were closed by some
    commit.

    Args:
        full_repo_name: the name of the github repo to search

    Return:
        a map commits -> set of closed issues
    """
    resolved_bugs: tp.Dict[str, tp.Set[str]] = defaultdict(set)

    def load_issue_events(github: Github) -> PaginatedList:
        repository: Repository = github.get_repo(full_repo_name)
        return repository.get_issues_events()

    cache_file_name = full_repo_name.replace("/", "_") + "_issues_events"
    issue_events: tp.Optional[
        tp.List[IssueEvent]] = get_cached_github_object(
            cache_file_name, load_issue_events)
    if issue_events:
        for issue_event in issue_events:
            if (issue_event.event == "closed" and
                    issue_event.commit_id is not None):
                resolved_bugs[issue_event.commit_id].add(
                    issue_event.issue.number)
        return resolved_bugs
    return {}
