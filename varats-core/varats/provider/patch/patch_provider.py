import os
import textwrap
import xml.etree.ElementTree as ET
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.project import Project
from benchbuild.utils import actions
from benchbuild.source.base import target_prefix
from benchbuild.utils.actions import StepResult
from benchbuild.utils.revision_ranges import (
    _get_all_revisions_between,
    _get_git_for_path
)
from plumbum import local

from varats.provider.provider import Provider, ProviderType
from varats.utils.git_util import CommitHash, ShortCommitHash


def __get_project_git(project: Project) -> tp.Optional[local.cmd]:
    return _get_git_for_path(
        local.path(project.source_of(project.primary_source)))


class ApplyPatch(actions.ProjectStep):
    """Apply a patch to a project."""

    NAME = "ApplyPatch"
    DESCRIPTION = "Apply a Git patch to a project."

    def __init__(self, project, patch):
        super().__init__(project)
        self.__patch = patch

    def __call__(self) -> StepResult:
        repo_git = __get_project_git(self.project)

        patch_path = self.__patch.path

        repo_git("apply", patch_path)

        return StepResult.OK

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(f"* {self.project.name}: "
                               f"Apply the patch "
                               f"'{self.__patch.shortname}' to the project.",
                               " " * indent)


class RevertPatch(actions.ProjectStep):
    """Revert a patch from a project."""

    NAME = "RevertPatch"
    DESCRIPTION = "Revert a Git patch from a project."

    def __init__(self, project, patch):
        super().__init__(project)
        self.__patch = patch

    def __call__(self) -> StepResult:
        repo_git = __get_project_git(self.project)

        patch_path = self.__patch.path

        repo_git("apply", "-R", patch_path)

        return StepResult.OK

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(f"* {self.project.name}: "
                               f"Revert the patch '{self.__patch.shortname}' "
                               f"from the project.",
                               " " * indent)


class Patch:
    """A class for storing a single project-specific Patch"""

    def __init__(self, project_name: str,
                 shortname: str,
                 description: str,
                 path: Path,
                 valid_revisions: tp.Optional[tp.Set[CommitHash]] = None):
        self.project_name: str = project_name
        self.shortname: str = shortname
        self.description: str = description
        self.path: Path = path
        self.valid_revisions: tp.Optional[tp.Set[CommitHash]] = valid_revisions


class ProjectPatchesConfiguration:
    """A class storing a set of patches specific to a project"""

    def __init__(self, project_name: str,
                 repository: str,
                 patches: tp.List[Patch]):
        self.project_name: str = project_name
        self.repository: str = repository
        self.patches: tp.List[Patch] = patches

    def get_patches_for_revision(self, revision: CommitHash) -> tp.Set[Patch]:
        """Returns all patches that are valid for the given revision"""

        return {p for p in self.patches if revision in p.valid_revisions}

    def get_by_shortname(self, shortname: str) -> tp.Optional[Patch]:
        """Returns the patch with the given shortname"""

        for patch in self.patches:
            if patch.shortname == shortname:
                return patch

        return None

    @staticmethod
    def from_xml(xml_path: Path):
        """Creates a ProjectPatchesConfiguration from an XML file"""

        base_dir = xml_path.parent

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
                    {ShortCommitHash(h) for h in
                     _get_all_revisions_between(start_tag.text.strip(),
                                                end_tag.text.strip(),
                                                repo_git)})

            return res

        # We explicitly ignore further validity checking of the XML
        # As for now, this is already done by a CI Job
        for patch in root.find("patches").findall("patch"):
            shortname = patch.findtext("shortname")
            description = patch.findtext("description")

            path = Path(patch.findtext("path"))

            if not path.is_absolute():
                path = base_dir / path

            include_revisions: tp.Set[CommitHash] = set()

            include_revs_tag = patch.find("include_revisions")

            if include_revs_tag:
                include_revisions = parse_revisions(include_revs_tag)
            else:
                include_revisions = {ShortCommitHash(h) for h in
                                     repo_git('log',
                                              '--pretty=%H',
                                              '--first-parent').strip().split()}

            exclude_revs_tag = patch.find("exclude_revisions")

            if exclude_revs_tag:
                revs = parse_revisions(exclude_revs_tag)
                include_revisions.difference_update(revs)

            patch_list.append(Patch(project_name,
                                    shortname,
                                    description,
                                    path,
                                    include_revisions))

        return ProjectPatchesConfiguration(project_name, repository, patch_list)


class PatchesNotFoundError(FileNotFoundError):
    # TODO: Implement me
    pass


class PatchProvider(Provider):
    """A provider for getting patch files for a certain project"""

    patches_repository = "git@github.com:se-sic/vara-project-patches.git"

    def __init__(self, project: tp.Type[Project]):
        super().__init__(project)

        patches_project_dir = Path(self._get_patches_repository_path()
                                   / self.project.NAME)

        # BB only performs a fetch so our repo might be out of date
        _get_git_for_path(patches_project_dir)("pull")

        if not patches_project_dir.is_dir():
            # TODO: Error handling/warning and None
            raise PatchesNotFoundError()

        conf_file = Path(patches_project_dir / ".patches.xml")

        if not conf_file.exists():
            # TODO: Error handling/warning and None
            raise PatchesNotFoundError()

        self.patches_config = ProjectPatchesConfiguration.from_xml(conf_file)

    @classmethod
    def create_provider_for_project(cls: tp.Type[ProviderType],
                                    project: tp.Type[Project]):
        """
                Creates a provider instance for the given project if possible.

                Returns:
                    a provider instance for the given project if possible,
                    otherwise, ``None``
        """
        try:
            return PatchProvider(project)
        except PatchesNotFoundError:
            # TODO: Warnings
            return None

    @classmethod
    def create_default_provider(cls: tp.Type[ProviderType],
                                project: tp.Type[Project]):
        """
                Creates a default provider instance that can be used with any project.

                Returns:
                    a default provider instance
        """
        raise AssertionError("All usages should be covered by the project specific provider.")

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


def create_patch_action_list(project: Project,
                             standard_actions: tp.MutableSequence[actions.Step],
                             commit: CommitHash) \
        -> tp.Mapping[str, tp.MutableSequence[actions.Step]]:
    """ Creates a map of actions for applying
    all patches that are valid for the given revision """
    result_actions = {}

    patch_provider = PatchProvider.create_provider_for_project(project)
    patches = patch_provider.patches_config.get_patches_for_revision(commit)

    for patch in patches:
        result_actions[patch.shortname] = [actions.MakeBuildDir(project),
                                           actions.ProjectEnvironment(project),
                                           ApplyPatch(project, patch),
                                           *standard_actions]

    return result_actions


def wrap_action_list_with_patch(action_list: tp.MutableSequence[actions.Step],
                                project: Project, patch: Patch) \
        -> tp.MutableSequence[actions.Step]:
    """ Wraps the given action list with the given patch """
    return [actions.MakeBuildDir(project),
            actions.ProjectEnvironment(project),
            ApplyPatch(project, patch),
            *action_list]
