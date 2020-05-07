"""Module for the :class:`CVEProvider`."""
import typing as tp

from benchbuild.project import Project

from varats.data.provider.cve.cve import CVE, find_all_cve, find_cve, find_cwe
from varats.data.provider.cve.cve_map import generate_cve_map
from varats.data.provider.provider import Provider
from varats.utils.project_util import get_local_project_git_path


class CVEProviderHook():
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
        raise NotImplementedError("Must be overridden by the project.")


class CVEProvider(Provider):
    """Provides CVE and CWE information for a project."""

    def __init__(self, project: tp.Type[Project]) -> None:
        super().__init__(project)
        if hasattr(project, "get_cve_product_info"):
            self.__cve_map = generate_cve_map(
                get_local_project_git_path(project.NAME),
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
        if hasattr(project, "get_cve_product_info"):
            return CVEProvider(project)
        return None

    @classmethod
    def create_default_provider(
        cls, project: tp.Type[Project]
    ) -> 'CVEProvider':
        return CVEDefaultProvider(project)

    def get_revision_cve_tuples(
        self
    ) -> tp.Set[tp.Tuple[str, tp.FrozenSet[CVE]]]:
        """
        Get all CVEs associated with this provider's project along with the
        fixing commits/versions.

        Return:
            a set of tuples of commit hash and cves
        """
        return {(k, frozenset(tp.cast(tp.Set[CVE], v["cve"])))
                for k, v in self.__cve_map.items()}


class CVEDefaultProvider(CVEProvider):
    """Default implementation of the :class:`CVE provider` for projects that do
    not (yet) support CVEs."""

    def __init__(self, project: tp.Type[Project]) -> None:
        # pylint: disable=E1003
        super(CVEProvider, self).__init__(project)

    def get_revision_cve_tuples(
        self
    ) -> tp.Set[tp.Tuple[str, tp.FrozenSet[CVE]]]:
        return set()


# TODO: remove below functions once we remove the cve driver
def list_cve_for_projects(
    vendor: str, product: str, verbose: bool = False
) -> None:
    """
    List all CVE's for the given vendor/product combination.

    Call via vara-sec list-cve <vendor> <product>.
    """
    print(f"Listing CVE's for {vendor}/{product}:")
    try:
        for cve in find_all_cve(vendor=vendor, product=product):
            if verbose:
                print(cve, end='\n\n')
            else:
                print(f'{cve.cve_id:20} [{cve.url}]')
    except ValueError:
        print('No entries found.')


def info(search: str, verbose: bool = False) -> None:
    """Search for matching CVE/CWE and print its data."""
    print(f"Fetching information for {search}:")

    if search.lower().startswith('cve-'):
        cve = find_cve(cve_id=search)
        if verbose:
            print(cve)
        else:
            print(f'{cve.cve_id:20} [{cve.url}]')
    elif search.lower().startswith('cwe-'):
        cwe = find_cwe(cwe_id=search)
        if verbose:
            print(cwe)
        else:
            print(f'{cwe.cwe_id:20} [{cwe.url}]')
    else:
        print(
            f'Could not parse input. Did you mean CVE-{search} or CWE-{search}?'
        )
