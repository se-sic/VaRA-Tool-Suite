"""Module for the :class:`CVEProvider`."""
import sys
import typing as tp

from benchbuild.project import Project

from varats.project.project_util import get_local_project_git_path
from varats.provider.cve.cve import CVE
from varats.provider.cve.cve_map import generate_cve_map, CVEDict
from varats.provider.provider import Provider
from varats.utils.git_util import FullCommitHash

if sys.version_info <= (3, 8):
    from typing_extensions import Protocol, runtime_checkable
else:
    from typing import Protocol, runtime_checkable


@runtime_checkable
class CVEProviderHook(Protocol):
    """
    Gives the :class:`CVEProvider` the necessary information how to find CVEs
    and CWEs for a project.

    This class should be inherited by projects.
    """

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        """
        Get information on how to find CVEs for a project.

        Returns:
            a tuple ``(vendor, product)``
        """


class CVEProvider(Provider):
    """Provides CVE and CWE information for a project."""

    def __init__(self, project: tp.Type[Project]) -> None:
        super().__init__(project)
        project_name = project.NAME
        if issubclass(project, CVEProviderHook):
            self.__cve_map: CVEDict = generate_cve_map(
                get_local_project_git_path(project_name),
                project.get_cve_product_info()
            )
        else:
            raise ValueError(
                f"Project {project} does not implement "
                f"CVEProviderHook."
            )

    @classmethod
    def create_provider_for_project(
        cls, project: tp.Type[Project]
    ) -> tp.Optional['CVEProvider']:
        if issubclass(project, CVEProviderHook):
            return CVEProvider(project)
        return None

    @classmethod
    def create_default_provider(
        cls, project: tp.Type[Project]
    ) -> 'CVEProvider':
        return CVEDefaultProvider(project)

    def get_revision_cve_tuples(
        self
    ) -> tp.Set[tp.Tuple[FullCommitHash, tp.FrozenSet[CVE]]]:
        """
        Get all CVEs associated with this provider's project along with the
        fixing commits/versions.

        Return:
            a set of tuples of commit hash and cves
        """
        return {(k, frozenset(v["cve"])) for k, v in self.__cve_map.items()}


class CVEDefaultProvider(CVEProvider):
    """Default implementation of the :class:`CVE provider` for projects that do
    not (yet) support CVEs."""

    def __init__(self, project: tp.Type[Project]) -> None:
        # pylint: disable=E1003
        super(CVEProvider, self).__init__(project)

    def get_revision_cve_tuples(
        self
    ) -> tp.Set[tp.Tuple[FullCommitHash, tp.FrozenSet[CVE]]]:
        return set()
