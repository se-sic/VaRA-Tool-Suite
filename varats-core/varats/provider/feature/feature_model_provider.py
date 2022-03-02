"""Module for the :class:`FeatureProvider`."""
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.project import Project
from benchbuild.source.base import target_prefix

from varats.provider.provider import Provider


class FeatureModelNotFound(FileNotFoundError):
    """Exception raised when the specified feature model could not be found."""

    def __init__(self, project: Project, fm_path: tp.Optional[Path]) -> None:
        err_msg = f"Could not find feature model for project {project.name}!\n"
        if fm_path:
            err_msg += f"No file at: {fm_path}."
        else:
            err_msg += "Got no feature-model path."

        super().__init__(err_msg)


class FeatureModelProvider(Provider):
    """Provider for accessing project related FeatureModels."""

    @classmethod
    def create_provider_for_project(
        cls, project: tp.Type[Project]
    ) -> tp.Optional['FeatureModelProvider']:
        """
        Creates a provider instance for the given project if possible.

        Returns:
            a provider instance for the given project if possible,
            otherwise, ``None``
        """
        return FeatureModelProvider(project)

    @classmethod
    def create_default_provider(
        cls, project: tp.Type[Project]
    ) -> 'FeatureModelProvider':
        """
        Creates a default provider instance that can be used with any project.

        Returns:
            a default provider instance
        """
        raise AssertionError(
            "All usages should be covered by the project specific provider."
        )

    def get_feature_model_path(
        self,
        # Currently, unused until pascals impl is ready
        revision: str  # pylint: disable=W0613
    ) -> tp.Optional[Path]:
        """
        Get the path to a feature model for a specific `revision` that describes
        the features of a project and their relationships. In case that no
        feature model exists `None` is returned.

        Args:
            revision: of the project, specifying for which state of the project
                      the feature model needs to be valid.

        Returns: a path to the corresponding feature model
        """
        project_name = self.project.NAME.lower()

        fully_qualified_fm_name = "FeatureModel"

        for project_dir in self._get_feature_model_repository_path().iterdir():
            if project_dir.name.lower() == project_name:
                for poss_fm_file in project_dir.iterdir():
                    if poss_fm_file.stem == fully_qualified_fm_name:
                        return poss_fm_file

        return None

    @staticmethod
    def _get_feature_model_repository_path() -> Path:
        fm_source = bb.source.Git(
            remote="https://github.com/Kaufi-Jonas/ConfigurableSystems.git",
            local="ConfigurableSystems",
            refspec="origin/HEAD",
            limit=1,
        )
        fm_source.fetch()

        return Path(Path(target_prefix()) / fm_source.local)
