import typing as tp

from benchbuild.project import Project

from varats.provider.provider import Provider
from varats.utils.filesystem_util import lock_file


class ArchitectureModelProvider(Provider):
    """Provider for accessing project related ArchitectureModels."""

    @classmethod
    def create_provider_for_project(
        cls, project: tp.Type[Project]
    ) -> tp.Optional['ArchitectureModelProvider']:
        """
        Creates a provider instance for the given project if possible.

        Returns:
            a provider instance for the given project if possible,
            otherwise, ``None``
        """
        return ArchitectureModelProvider(project)

    @classmethod
    def create_default_provider(
        cls, project: tp.Type[Project]
    ) -> 'ArchitectureModelProvider':
        """
        Creates a default provider instance that can be used with any project.

        Returns:
            a default provider instance
        """
        raise AssertionError(
            "All usages should be covered by the project specific provider."
        )

    def get_architecture_model_path(self, project: Project) -> str:
        """
        Get the path to the architecture model for the given project.

        Args:
            project: The project to get the architecture model for.

        Returns:
            The path to the architecture model.
        """
        return f"/home/simon/Workspace/Uni/Vara/vara/example.yaml"
