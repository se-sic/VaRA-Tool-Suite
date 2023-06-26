import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.project import Project
from benchbuild.source.base import target_prefix

from varats.provider.patch.patch import Patch, ProjectPatchesConfiguration
from varats.provider.provider import Provider, ProviderType


class PatchesNotFoundError(FileNotFoundError):
    # TODO: Implement me
    pass


class PatchProvider(Provider):
    """A provider for getting patch files for a certain project"""

    patches_repository = "https://github.com/se-sic/vara-project-patches.git"

    def __init__(self, project: tp.Type[Project]):
        patches_project_dir = Path(self._get_patches_repository_path() / self.project.NAME)

        if not patches_project_dir.is_dir():
            # TODO: Add proper error message
            raise PatchesNotFoundError()

        patches_config_file = Path(patches_project_dir / "test-patch-configuration.xml")

        if not patches_config_file.exists():
            # TODO: Add proper error handling
            # This should probably be a different error since it is related to the patches config
            # not the patches itself
            raise PatchesNotFoundError()

        self.project_patches = self._parse_patches_config(patches_config_file)

        super().__init__(project)

    @classmethod
    def create_provider_for_project(cls: tp.Type[ProviderType], project: tp.Type[Project]) -> tp.Optional[ProviderType]:
        pass

    @classmethod
    def create_default_provider(cls: tp.Type[ProviderType], project: tp.Type[Project]) -> ProviderType:
        pass

    @staticmethod
    def _get_patches_repository_path() -> Path:
        patches_source = bb.source.Git(
            remote=PatchProvider.patches_repository,
            local="ConfigurableSystems",
            refspec="origin/HEAD",
            limit=1,
        )

        patches_source.fetch()

        return Path(Path(target_prefix()) / patches_source.local)

    @staticmethod
    def _parse_patches_config(config_file: Path) -> ProjectPatchesConfiguration:
        # TODO: Implement XML parsing for patches config
        pass

