import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.project import Project
from benchbuild.source.base import target_prefix

from varats.provider.provider import Provider
from varats.utils.filesystem_util import lock_file


class ArchitectureModelProvider(Provider):
    """Provider for accessing project related ArchitectureModels."""

    am_repository = "https://github.com/Sinerum/ArchitectureModels.git"

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

    def get_architecture_model_path(
        self,
        # Currently, unused until pascals impl is ready
        revision: str  # pylint: disable=W0613
    ) -> tp.Optional[Path]:
        """
        Get the path to a architecture model for a specific `revision` that
        describes the architectures of a project and their relationships. In
        case that no architecture model exists `None` is returned.

        Args:
            revision: of the project, specifying for which state of the project
                      the architecture model needs to be valid.

        Returns: a path to the corresponding architecture model
        """
        project_name = self.project.NAME.lower()

        fully_qualified_am_name = "ArchitectureModel"

        for project_dir in self._get_architecture_model_repository_path(
        ).iterdir():
            if project_dir.name.lower() == project_name:
                for poss_am_file in project_dir.iterdir():
                    if poss_am_file.stem == fully_qualified_am_name:
                        return poss_am_file

        return None

    @staticmethod
    def _get_architecture_model_repository_path() -> Path:
        fm_source = bb.source.Git(
            remote=ArchitectureModelProvider.am_repository,
            local="ArchitectureModels",
            refspec="origin/HEAD",
            limit=1,
        )

        lock_path = Path(target_prefix()) / "am_provider.lock"
        with lock_file(lock_path):
            fm_source.fetch()

        return Path(Path(target_prefix()) / fm_source.local)
