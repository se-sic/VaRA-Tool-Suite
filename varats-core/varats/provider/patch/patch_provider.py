import os
import textwrap
import typing as tp
from pathlib import Path

import benchbuild as bb
import yaml
from benchbuild.project import Project
from benchbuild.source.base import target_prefix
from benchbuild.utils import actions
from benchbuild.utils.actions import StepResult
from benchbuild.utils.revision_ranges import (
    _get_all_revisions_between,
    _get_git_for_path,
)
from plumbum import local, ProcessExecutionError

from varats.project.project_util import get_local_project_git_path
from varats.project.varats_project import VProject
from varats.provider.provider import Provider, ProviderType
from varats.utils.git_commands import (
    pull_current_branch,
    apply_patch,
    revert_patch,
)
from varats.utils.git_util import (
    CommitHash,
    ShortCommitHash,
    get_all_revisions_between,
)


def __get_project_git(project: Project):
    return _get_git_for_path(
        local.path(project.source_of(project.primary_source))
    )


class ApplyPatch(actions.ProjectStep):
    """Apply a patch to a project."""

    NAME = "APPLY_PATCH"
    DESCRIPTION = "Apply a Git patch to a project."

    def __init__(self, project: VProject, patch: 'Patch') -> None:
        super().__init__(project)
        self.__patch = patch

    def __call__(self) -> StepResult:
        try:
            print(
                f"Applying {self.__patch.shortname} to "
                f"{self.project.source_of(self.project.primary_source)}"
            )
            apply_patch(
                Path(self.project.source_of(self.project.primary_source)),
                self.__patch.path
            )

        except ProcessExecutionError:
            self.status = StepResult.ERROR

        self.status = StepResult.OK

        return StepResult.OK

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Apply patch "
            f"{self.__patch.shortname}", " " * indent
        )


class RevertPatch(actions.ProjectStep):
    """Revert a patch from a project."""

    NAME = "REVERT_PATCH"
    DESCRIPTION = "Revert a Git patch from a project."

    def __init__(self, project, patch):
        super().__init__(project)
        self.__patch = patch

    def __call__(self) -> StepResult:
        try:
            print(
                f"Reverting {self.__patch.shortname} on "
                f"{self.project.source_of(self.project.primary_source)}"
            )
            revert_patch(
                Path(self.project.source_of(self.project.primary_source)),
                self.__patch.path
            )

        except ProcessExecutionError:
            self.status = StepResult.ERROR

        self.status = StepResult.OK

        return StepResult.OK

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Revert patch "
            f"{self.__patch.shortname}", " " * indent
        )


class Patch:
    """A class for storing a single project-specific Patch."""

    def __init__(
        self,
        project_name: str,
        shortname: str,
        description: str,
        path: Path,
        valid_revisions: tp.Optional[tp.Set[CommitHash]] = None,
        tags: tp.Optional[tp.Set[str]] = None
    ):
        self.project_name: str = project_name
        self.shortname: str = shortname
        self.description: str = description
        self.path: Path = path
        self.valid_revisions: tp.Optional[tp.Set[CommitHash]] = valid_revisions
        self.tags: tp.Optional[tp.Set[str]] = tags

    @staticmethod
    def from_yaml(yaml_path: Path):
        """Creates a Patch from a YAML file."""

        yaml_dict = yaml.safe_load(yaml_path.read_text())

        if not yaml_dict:
            # TODO: Proper Error/warning
            raise PatchesNotFoundError()

        project_name = yaml_dict["project_name"]
        shortname = yaml_dict["shortname"]
        description = yaml_dict["description"]
        path = yaml_dict["path"]
        # Convert to full qualified path, as we know that path is relative to
        # the yaml info file.
        path = yaml_path.parent / path

        tags = None
        if "tags" in yaml_dict:
            tags = yaml_dict["tags"]

        main_repo_git = _get_git_for_path(
            get_local_project_git_path(project_name)
        )

        def parse_revisions(rev_dict: tp.Dict) -> tp.Set[CommitHash]:
            res: tp.Set[CommitHash] = set()

            if "single_revision" in rev_dict:
                if isinstance(rev_dict["single_revision"], str):
                    res.add(ShortCommitHash(rev_dict["single_revision"]))
                else:
                    res.update([
                        ShortCommitHash(r) for r in rev_dict["single_revision"]
                    ])

            if "revision_range" in rev_dict:
                if isinstance(rev_dict["revision_range"], list):
                    for rev_range in rev_dict["revision_range"]:
                        res.update(
                            get_all_revisions_between(
                                rev_range["start"], rev_range["end"],
                                ShortCommitHash,
                                get_local_project_git_path(project_name)
                            )
                        )
                else:
                    res.update({
                        ShortCommitHash(h) for h in _get_all_revisions_between(
                            rev_dict["revision_range"]["start"],
                            rev_dict["revision_range"]["end"], main_repo_git
                        )
                    })

            return res

        if "include_revisions" in yaml_dict:
            include_revisions = parse_revisions(yaml_dict["include_revisions"])
        else:
            include_revisions = {
                ShortCommitHash(h)
                for h in main_repo_git('log', '--pretty=%H', '--first-parent'
                                      ).strip().split()
            }

        if "exclude_revisions" in yaml_dict:
            include_revisions.difference_update(
                parse_revisions(yaml_dict["exclude_revisions"])
            )

        return Patch(
            project_name, shortname, description, path, include_revisions, tags
        )

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        valid_revs = [str(r) for r in self.valid_revisions
                     ] if self.valid_revisions else []
        str_representation = f"""Patch(
    ProjectName: {self.project_name}
    Shortname: {self.shortname}
    Path: {self.path}
    ValidRevs: {valid_revs}
)
"""

        return str_representation


class PatchSet:

    def __init__(self, patches: tp.Set[Patch]):
        self.__patches: tp.FrozenSet[Patch] = frozenset(patches)

    def __iter__(self) -> tp.Iterator[Patch]:
        return self.__patches.__iter__()

    def __contains__(self, v: tp.Any) -> bool:
        return self.__patches.__contains__(v)

    def __len__(self) -> int:
        return len(self.__patches)

    def __getitem__(self, tag):
        tag_set = set(tag)
        return PatchSet({p for p in self.__patches if tag_set.issubset(p.tags)})

    def __and__(self, rhs: "PatchSet") -> "PatchSet":
        lhs_t = self.__patches
        rhs_t = rhs.__patches

        ret = {}
        ...
        return ret

    def __or__(self, rhs: "PatchSet") -> "PatchSet":
        lhs_t = self.__patches
        rhs_t = rhs.__patches

        ret = {}
        ...
        return ret

    def __hash__(self) -> int:
        return hash(self.__patches)

    def __repr__(self) -> str:
        repr_str = ", ".join([f"{k.shortname}" for k in self.__patches])

        return f"PatchSet({{{repr_str}}})"


class PatchesNotFoundError(FileNotFoundError):
    # TODO: Implement me
    pass


class PatchProvider(Provider):
    """A provider for getting patch files for a certain project."""

    patches_repository = "git@github.com:se-sic/vara-project-patches.git"

    def __init__(self, project: tp.Type[Project]):
        super().__init__(project)

        # BB only performs a fetch so our repo might be out of date
        pull_current_branch(self._get_patches_repository_path())

        patches_project_dir = Path(
            self._get_patches_repository_path() / self.project.NAME
        )

        if not patches_project_dir.is_dir():
            # TODO: Error handling/warning and None
            raise PatchesNotFoundError()

        patches = set()

        for root, dirs, files in os.walk(patches_project_dir):
            for filename in files:
                if not filename.endswith(".info"):
                    continue

                info_path = Path(os.path.join(root, filename))
                current_patch = Patch.from_yaml(info_path)

                patches.add(current_patch)

        self.__patches: tp.Set[Patch] = patches

    def get_by_shortname(self, shortname: str) -> tp.Optional[Patch]:
        for patch in self.__patches:
            if patch.shortname == shortname:
                return patch

        return None

    def get_patches_for_revision(self, revision: CommitHash) -> PatchSet:
        """Returns all patches that are valid for the given revision."""
        return PatchSet({
            p for p in self.__patches if revision in p.valid_revisions
        })

    @classmethod
    def create_provider_for_project(
        cls: tp.Type[ProviderType], project: tp.Type[Project]
    ):
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
    def create_default_provider(
        cls: tp.Type[ProviderType], project: tp.Type[Project]
    ):
        """
        Creates a default provider instance that can be used with any project.

        Returns:
            a default provider instance
        """
        raise AssertionError(
            "All usages should be covered by the project specific provider."
        )

    @staticmethod
    def _get_patches_repository_path() -> Path:
        patches_source = bb.source.Git(
            remote=PatchProvider.patches_repository,
            local="patch-configurations",
            refspec="origin/f-StaticAnalysisMotivatedSynthBenchmarksImpl",
            limit=None,
            shallow=False
        )

        patches_source.fetch()

        return Path(target_prefix()) / patches_source.local
