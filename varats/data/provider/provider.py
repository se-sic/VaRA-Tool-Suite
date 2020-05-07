"""
Provider interface module for projects.

Providers are a means to supply additional data for a project.
"""
import logging
import typing as tp
from abc import ABC, abstractmethod

from benchbuild.project import Project

LOG = logging.getLogger(__name__)

ProviderType = tp.TypeVar("ProviderType", bound="Provider")


class Provider(ABC):
    """
    A provider allows access to additional information about a project, e.g.,
    which revisions of a project are releases, or which CVE's are related to a
    project.

    Args:
        project: the project this provider is associated with
    """

    def __init__(self, project: tp.Type[Project]) -> None:
        self.__project = project

    @property
    def project(self) -> tp.Type[Project]:
        """The project this provider is associated with."""
        return self.__project

    @classmethod
    @abstractmethod
    def create_provider_for_project(
        cls: tp.Type[ProviderType], project: tp.Type[Project]
    ) -> tp.Optional[ProviderType]:
        """
        Creates a provider instance for the given project if possible.

        Returns:
            a provider instance for the given project if possible,
            otherwise, ``None``
        """

    @classmethod
    @abstractmethod
    def create_default_provider(
        cls: tp.Type[ProviderType], project: tp.Type[Project]
    ) -> ProviderType:
        """
        Creates a default provider instance that can be used with any project.

        Returns:
            a default provider instance
        """

    @classmethod
    def get_provider_for_project(
        cls: tp.Type[ProviderType], project: tp.Type[Project]
    ) -> ProviderType:
        """
        Factory function for creating providers.

        This function is guaranteed to return a valid instance of the requested
        provider by falling back to a
        :func:`default provider<Provider.create_default_provider>` if necessary.
        A warning is issued in the latter case.

        Args:
            project: the project to create the provider for

        Returns:
            an instance of this provider
        """
        provider = cls.create_provider_for_project(project)
        if provider is not None:
            return provider

        LOG.warning(
            f"{str(cls)} does not support the project {project.NAME}. "
            f"Using default provider instance."
        )
        return cls.create_default_provider(project)
