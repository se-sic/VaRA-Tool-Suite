"""
Module for the :class:`ReleaseProvider`.
"""
import typing as tp
from enum import Enum

from packaging.version import parse as parse_version, Version

from benchbuild.project import Project

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
        Merges two release type.
        It is assumed that minor releases include major releases
        and patch releases include minor releases.
        """
        if other is None:
            return self
        return self if self.value >= other.value else other


class ReleaseProviderHook():
    """
    Gives the :class:`ReleaseProvider` the necessary information how to find the
    releases for a project.

    This class should be inherited by projects.
    """

    @classmethod
    def get_release_revisions(
            cls, release_type: ReleaseType) -> tp.List[tp.Tuple[str, str]]:
        """
        Get a set of all release revisions for a project

        Returns:
            a list of tuples of hashes and version strings of release commits
        """
        raise NotImplementedError("Must be overridden by the project.")


class ReleaseProvider(Provider):
    """
    Provides CVE and CWE information for a project.
    """

    def __init__(self, project: tp.Type[Project]) -> None:
        super().__init__(project)
        if hasattr(project, "get_release_revisions"):
            self.hook = tp.cast(ReleaseProviderHook, project)
        else:
            raise ValueError(f"Project {project} does not implement "
                             f"ReleaseProviderHook.")

    @classmethod
    def create_provider_for_project(
            cls, project: tp.Type[Project]) -> tp.Optional['ReleaseProvider']:
        if hasattr(project, "get_release_revisions"):
            return ReleaseProvider(project)
        return None

    @classmethod
    def create_default_provider(cls,
                                project: tp.Type[Project]) -> 'ReleaseProvider':
        return ReleaseDefaultProvider(project)

    def get_release_revisions(
            self, release_type: ReleaseType) -> tp.List[tp.Tuple[str, str]]:
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
    Default implementation of the :class:`ReleaseProvider` for projects that
    do not need or support their own implementation. This implementation looks
    for commits with tags that are
    :ref:`PEP 440<https://www.python.org/dev/peps/pep-0440/>` versions.
    """

    def __init__(self, project: tp.Type[Project]) -> None:
        # pylint: disable=E1003
        super(ReleaseProvider, self).__init__(project)

    def get_release_revisions(
            self, release_type: ReleaseType) -> tp.List[tp.Tuple[str, str]]:
        tagged_commits = get_tagged_commits(self.project.NAME)
        return [(h, tag)
                for h, tag in tagged_commits
                if isinstance(parse_version(tag), Version)]
