"""
Module for the :class:`CVEProvider`.
"""
import typing as tp
from abc import ABC, abstractmethod

from benchbuild.project import Project

from varats.data.provider.cve.cve import (find_all_cve, find_cve, find_cwe,
                                          CVE)
from varats.data.provider.provider import Provider


class CVEProviderHook(ABC):
    """
    Gives the :class:`CVEProvider` the necessary information how to find CVEs
    and CWEs for a project.

    This abstract class should be inherited by projects.
    """

    @abstractmethod
    def get_cve_product_info(self) -> tp.Tuple[str, str]:
        """
        Get information on how to find CVEs for a project.

        Returns:
            a tuple ``(vendor, product)``
        """


class CVEProvider(Provider):
    """
    Provides CVE and CWE information for a project.
    """

    def __init__(self, project: Project) -> None:
        super().__init__(project)
        if isinstance(project, CVEProviderHook):
            vendor, product = project.get_cve_product_info()
            self.__cves = set(
                find_all_cve(vendor=vendor, product=product))
        else:
            raise ValueError(f"Project {project.NAME} does not implement "
                             f"CVEProviderInformation.")

    @classmethod
    def create_provider_for_project(
            cls, project: Project) -> tp.Optional['CVEProvider']:
        if isinstance(project, CVEProviderHook):
            return CVEProvider(project)
        return None

    @classmethod
    def create_default_provider(cls, project: Project) -> 'CVEProvider':
        return CVEDefaultProvider(project)

    def get_cves(self) -> tp.Set[CVE]:
        """
        Get a set of CVE's for this project
        """
        return self.__cves

    def get_revision_cve_tuples(self) -> tp.Set[tp.Tuple[str, CVE]]:
        return {("", cve) for cve in self.get_cves()}


class CVEDefaultProvider(CVEProvider):
    """
    Default implementation of the :class:`CVE provider` for projects that
    do not (yet) support CVEs.
    """

    def get_cves(self) -> tp.Set[CVE]:
        return set()


# TODO: remove below functions once we remove the cve driver
def list_cve_for_projects(vendor: str,
                          product: str,
                          verbose: bool = False) -> None:
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
    """
    Search for matching CVE/CWE and print its data.
    """
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
