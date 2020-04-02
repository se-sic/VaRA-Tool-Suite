"""
Module for the :class:`CVEProvider`.
"""
import re
import typing as tp
from collections import defaultdict

from benchbuild.project import Project
from github import Github
from github.Repository import Repository

from varats.data.provider.provider import Provider


GITHUB_URL_PATTERN = re.compile(r"https://github\.com/(.*)/(.*)\.git")


class BugProvider(Provider):
    """
    Provides CVE and CWE information for a project.
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
        Get all CVEs associated with this provider's project along with the
        fixing commits/versions.

        Return:
            a set of tuples of commit hash and cves
        """
        if self.__github_project_name:
            return get_github_bugs(self.__github_project_name)
        return {}


class BugDefaultProvider(BugProvider):
    """
    Default implementation of the :class:`CVE provider` for projects that
    do not (yet) support CVEs.
    """

    def __init__(self, project: tp.Type[Project]) -> None:
        # pylint: disable=E1003
        super(BugProvider, self).__init__(project)

    def get_resolved_bugs(self) -> tp.Dict[str, tp.Set[str]]:
        return {}


def get_github_bugs(full_repo_name: str) -> tp.Dict[str, tp.Set[str]]:
    resolved_bugs: tp.Dict[str, tp.Set[str]] = defaultdict(set)

    github = Github()
    repository: Repository = github.get_repo(full_repo_name)
    issues_events = repository.get_issues_events()
    for issue_event in issues_events:
        if issue_event.event == "closed" and issue_event.commit_id is not None:
            resolved_bugs[issue_event.commit_id].add(issue_event.issue.number)

    return resolved_bugs
