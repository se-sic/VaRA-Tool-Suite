"""Module for the :class:`ReleaseProvider`."""
import typing as tp
from enum import Enum

from benchbuild.project import Project
from packaging.version import Version
from packaging.version import parse as parse_version

from varats.data.provider.provider import Provider
from varats.utils.project_util import get_tagged_commits


class ReleaseType(Enum):
    """
    A ReleaseType referes to one of the three parts of the semantic versioning
    specification.

    It is assumed that a major release is also a minor release and that a minor
    release is also a patch release.
    """

    major = 1
    minor = 2
    patch = 3

    def merge(self, other: tp.Optional["ReleaseType"]) -> "ReleaseType":
        """
        Merges two release type. It is assumed that minor releases include major
        releases and patch releases include minor releases.

        >>> ReleaseType.minor.merge(ReleaseType.major)
        <ReleaseType.minor: 2>

        >>> ReleaseType.major.merge(ReleaseType.patch)
        <ReleaseType.patch: 3>
        """
        if other is None:
            return self
        # Pylint incorrectly issues a warning here.
        # pylint: disable=W0143
        return self if self.value >= other.value else other


class ReleaseProviderHook():
    """
    Gives the :class:`ReleaseProvider` the necessary information how to find the
    releases for a project.

    This class should be inherited by projects.
    """

    @classmethod
    def get_release_revisions(
        cls, release_type: ReleaseType
    ) -> tp.List[tp.Tuple[str, str]]:
        """
        Get a set of all release revisions for a project.

        Returns:
            a list of tuples of hashes and version strings of release commits
        """
        raise NotImplementedError("Must be overridden by the project.")


class ReleaseProvider(Provider):
    """Provides access to release revisions of a project."""

    def __init__(self, project: tp.Type[Project]) -> None:
        super().__init__(project)
        if hasattr(project, "get_release_revisions"):
            self.hook = tp.cast(ReleaseProviderHook, project)
        else:
            raise ValueError(
                f"Project {project} does not implement "
                f"ReleaseProviderHook."
            )

    @classmethod
    def create_provider_for_project(
        cls, project: tp.Type[Project]
    ) -> tp.Optional['ReleaseProvider']:
        if hasattr(project, "get_release_revisions"):
            return ReleaseProvider(project)
        return None

    @classmethod
    def create_default_provider(
        cls, project: tp.Type[Project]
    ) -> 'ReleaseProvider':
        return ReleaseDefaultProvider(project)

    def get_release_revisions(
        self, release_type: ReleaseType
    ) -> tp.List[tp.Tuple[str, str]]:
        """
        Get all release revisions of this provider's project along with their
        version strings.

        Args:
            release_type: the type of releases to return

        Return:
            a list of tuples of hashes and version strings of release commits
        """
        return self.hook.get_release_revisions(release_type)


class ReleaseDefaultProvider(ReleaseProvider):
    """
    Default implementation of the :class:`ReleaseProvider` for projects that do
    not need or support their own implementation.

    This implementation looks for commits with tags that are `PEP 440
    <https://www.python.org/dev/peps/pep-0440/>`_ versions.
    """

    def __init__(self, project: tp.Type[Project]) -> None:
        # pylint: disable=E1003
        super(ReleaseProvider, self).__init__(project)
        tagged_commits = get_tagged_commits(self.project.NAME)
        releases = [
            (commit, tag, parse_version(tag)) for commit, tag in tagged_commits
        ]
        self.releases = [(commit, tag, version)
                         for commit, tag, version in releases
                         if isinstance(version, Version)]

    def get_release_revisions(
        self, release_type: ReleaseType
    ) -> tp.List[tp.Tuple[str, str]]:
        if release_type is ReleaseType.patch:
            return [(commit, tag)
                    for commit, tag, version in self.releases
                    if not version.is_prerelease]
        if release_type is ReleaseType.minor:
            return [(commit, tag)
                    for commit, tag, version in self.releases
                    if version.micro == 0]
        if release_type is ReleaseType.major:
            return [(commit, tag)
                    for commit, tag, version in self.releases
                    if version.minor == 0]
        return []
