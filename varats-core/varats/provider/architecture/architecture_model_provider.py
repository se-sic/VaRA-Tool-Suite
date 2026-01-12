import typing as tp
from pathlib import Path

import benchbuild as bb
import yaml
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

    def get_architecture_model_path(self,) -> tp.Optional[Path]:
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

    def get_architecture_model(self):
        am_path = self.get_architecture_model_path()
        if am_path is None:
            raise ArchitectureModelNotFound(self.project, am_path)
        return ArchitectureModel(am_path, self.project.NAME)

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


class ArchitectureModelNotFound(Exception):
    """Exception to be raised if no architecture model could be found for a
    project."""

    def __init__(
        self, project: tp.Type[Project], path: tp.Optional[Path]
    ) -> None:
        self.project = project
        self.path = path
        super().__init__(self.__str__())

    def __str__(self) -> str:
        if self.path is None:
            return f"No architecture model found for project {self.project.NAME}"
        return f"No architecture model found for project {self.project.NAME} at {self.path}"


class ArchitectureModel:
    """Class representing an architecture model."""

    class Location:
        """Class representing a file, start- and end-line in an architecture
        model."""

        def __init__(
            self, file: str, start_line: tp.Optional[int],
            end_line: tp.Optional[int]
        ) -> None:
            self.file = file
            self.start_line = start_line
            self.end_line = end_line

    def __init__(self, path: Path, project: str) -> None:
        self.path = path
        with open(path, 'r') as stream:
            documents = yaml.load_all(stream, Loader=yaml.CLoader)
            raw_model = next(documents)
            raw_module_definitions = raw_model["Modules"]
            self.modules: tp.Dict[str, tp.List[ArchitectureModel.Location]] = {}
            for raw_module_definition in raw_module_definitions:
                self.modules[raw_module_definition["Name"]] = [
                    ArchitectureModel.Location(
                        loc["File"],
                        loc["StartLine"] if "StartLine" in loc else None,
                        loc["EndLine"] if "EndLine" in loc else None
                    ) for loc in raw_module_definition["Locations"]
                ]
            raw_package_definitions = raw_model["Packages"]
            self.packages: tp.Dict[str, tp.List[str]] = {}
            for raw_package_definition in raw_package_definitions:
                self.packages[raw_package_definition["Name"]] = \
                    raw_package_definition["Modules"]

    def get_module_for_location(self,
                                file: str,
                                line: tp.Optional[int] = None
                               ) -> tp.Optional[str]:
        """
        Get the module a specific file and line belongs to.

        Args:
            file: file to look for
            line: line in the file to look for

        Returns:
            the module name if found, otherwise None
        """
        for module, locations in self.modules.items():
            for location in locations:
                if location.file.endswith(file):
                    if not line:
                        return module
                    if (
                        location.start_line is None or
                        location.start_line <= line
                    ) and (
                        location.end_line is None or location.end_line >= line
                    ):
                        return module
        return file
