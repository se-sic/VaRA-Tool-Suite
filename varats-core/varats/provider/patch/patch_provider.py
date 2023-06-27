import os
import xml.etree.ElementTree as ET
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.project import Project
from benchbuild.source.base import target_prefix
from benchbuild.utils.revision_ranges import _get_all_revisions_between, _get_git_for_path

from varats.project.project_util import get_local_project_git_path
from varats.provider.provider import Provider, ProviderType
from varats.utils.git_util import CommitHash, ShortCommitHash


class Patch:
    """A class for storing a single project-specific Patch"""

    def __init__(self, project: str, shortname: str, description: str, path: Path,
                 valid_revisions: tp.Optional[tp.Set[CommitHash]] = None
                 , invalid_revisions: tp.Optional[tp.Set[CommitHash]] = None):
        self.project: str = project
        self.shortname: str = shortname
        self.description: str = description
        self.path: Path = path
        self.valid_revisions: tp.Set[CommitHash] = valid_revisions
        self.invalid_revisions: tp.Set[CommitHash] = invalid_revisions


class ProjectPatchesConfiguration:
    """A class storing a set of patches specific to a project"""

    def __init__(self, project_name: str, repository: str, patches: tp.List[Patch]):
        self.project_name: str = project_name
        self.repository: str = repository
        self.patches: tp.List[Patch] = patches

    def get_patches_for_revision(self, revision: CommitHash) -> tp.Set[Patch]:
        """Returns all patches that are valid for the given revision"""

        return {patch for patch in self.patches if revision in patch.valid_revisions}

    def get_by_shortname(self, shortname: str) -> tp.Optional[Patch]:
        """Returns the patch with the given shortname"""

        for patch in self.patches:
            if patch.shortname == shortname:
                return patch

        return None

    @staticmethod
    def from_xml(xml_path: Path):
        project_name: str = Path(os.path.abspath(xml_path)).parts[-2]
        tree = ET.parse(xml_path)
        root = tree.getroot()

        if len(root.findall("repository")) != 1:
            # TODO: Proper error handling
            raise RuntimeError("Only one repository allowed")

        repository = root.findtext("repository")

        project_git_source = bb.source.Git(
            remote=repository,
            local=project_name,
            refspec="origin/HEAD",
            shallow=False,
        )

        project_git_source.fetch()

        repo_git = _get_git_for_path(target_prefix() + "/" + project_name)
        patch_list: tp.List[Patch] = []

        def parse_revisions(revisions_tag: ET.Element) -> tp.Set[CommitHash]:
            res: tp.Set[CommitHash] = set()

            for revision_tag in revisions_tag.findall("single_revision"):
                res.add(ShortCommitHash(revision_tag.text.strip()))

            for revision_range_tag in revisions_tag.findall("revision_range"):
                start_tag = revision_range_tag.find("start")
                end_tag = revision_range_tag.find("end")

                res.update(
                    {ShortCommitHash(h) for h in _get_all_revisions_between(start_tag.text.strip(),
                                                                            end_tag.text.strip(),
                                                                            repo_git)})

            return res

        # We explicitly ignore further validity checking of the XML at that point
        # As for now, this is already done by a CI Job in the vara-project-patches
        # repository
        for patch in root.find("patches").findall("patch"):
            shortname = patch.findtext("shortname")
            description = patch.findtext("description")
            path = Path(patch.findtext("path"))

            include_revisions: tp.Set[CommitHash] = set()

            include_revs_tag = patch.find("include_revisions")

            if include_revs_tag:
                include_revisions = parse_revisions(include_revs_tag)
            else:
                include_revisions = { ShortCommitHash(h) for h in repo_git('log', '--pretty=%H', '--first-parent').strip().split() }

            exclude_revs_tag = patch.find("exclude_revisions")

            if exclude_revs_tag:
                include_revisions.difference_update(parse_revisions(exclude_revs_tag))

            patch_list.append(Patch(project_name, shortname, description, path, include_revisions))

        return ProjectPatchesConfiguration(project_name, repository, patch_list)


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
            local="patch-configurations",
            refspec="origin/HEAD",
            limit=1,
        )

        patches_source.fetch()

        return Path(Path(target_prefix()) / patches_source.local)

    @staticmethod
    def _parse_patches_config(config_file: Path) -> ProjectPatchesConfiguration:
        # TODO: Implement XML parsing for patches config
        pass
