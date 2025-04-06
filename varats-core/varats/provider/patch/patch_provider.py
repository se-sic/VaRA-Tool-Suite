"""
Module for the :class:`PatchProvider`.

The patch provider enables users to query patches for project, which can be
applied during an experiment to alter the state of the project.
"""

import os
import typing as tp
import warnings
from pathlib import Path

import benchbuild as bb
import yaml
from benchbuild.project import Project
from benchbuild.source.base import target_prefix
from yaml import YAMLError

from varats.project.project_util import get_local_project_repo
from varats.provider.provider import Provider, ProviderType
from varats.utils.filesystem_util import lock_file
from varats.utils.git_commands import pull_current_branch, fetch_repository
from varats.utils.git_util import (
    CommitHash,
    ShortCommitHash,
    get_all_revisions_between,
    get_initial_commit,
    RepositoryHandle,
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
        tags: tp.Optional[tp.Set[str]] = None,
        feature_tags: tp.Optional[tp.Set[str]] = None,
        regression_severity: tp.Optional[int] = None
    ):
        """
        Args:
            project_name: Project name that this patch belongs to
            shortname: Short name to uniquely identify a patch
            description: Textual description of the patch
            path: Path to the patch file
            valid_revisions: List of revisions that the patch is applicable to
            tags: Tags of the patch
            feature_tags: Feature specific tags of a patch (Used for PatchConfiguration)
            regression_severity: Regression severity in milliseconds (If applicable)
        """
        self.project_name: str = project_name
        self.shortname: str = shortname
        self.description: str = description
        self.path: Path = path
        self.valid_revisions: tp.Set[
            CommitHash] = valid_revisions if valid_revisions else set()
        self.tags: tp.Optional[tp.Set[str]] = tags
        self.feature_tags: tp.Optional[tp.Set[str]] = feature_tags
        self.regression_severity: tp.Optional[int] = regression_severity

    @staticmethod
    def from_yaml(yaml_path: Path) -> 'Patch':
        """Creates a Patch from a YAML file."""

        yaml_dict = yaml.safe_load(yaml_path.read_text())

        project_name = yaml_dict["project_name"]
        shortname = yaml_dict["shortname"]
        description = yaml_dict["description"]
        path = yaml_dict["path"]
        # Convert to full qualified path, as we know that path is relative to
        # the yaml info file.
        path = yaml_path.parent / path

        tags = yaml_dict.get("tags")
        feature_tags = yaml_dict.get("feature_tags")

        project_repo = get_local_project_repo(project_name)

        def parse_revisions(
            rev_dict: tp.Dict[str, tp.Any]
        ) -> tp.Set[CommitHash]:
            res: tp.Set[CommitHash] = set()

            if "single_revision" in rev_dict:
                if isinstance(rev_dict["single_revision"], str):
                    res.add(ShortCommitHash(rev_dict["single_revision"]))
                else:
                    res.update([
                        ShortCommitHash(r) for r in rev_dict["single_revision"]
                    ])

            if "revision_range" in rev_dict:
                rev_ranges = rev_dict["revision_range"]
                if not isinstance(rev_ranges, list):
                    rev_ranges = [rev_ranges]
                for rev_range in rev_ranges:
                    if "end" in rev_range:
                        end_rev = rev_range["end"]
                    else:
                        end_rev = ""
                    res.update(
                        get_all_revisions_between(
                            project_repo, rev_range["start"], end_rev,
                            ShortCommitHash
                        )
                    )

            return res

        include_revisions: tp.Set[CommitHash]
        if "include_revisions" in yaml_dict:
            include_revisions = parse_revisions(yaml_dict["include_revisions"])
        else:
            include_revisions = set(
                get_all_revisions_between(
                    project_repo,
                    get_initial_commit(project_repo).hash, "", ShortCommitHash
                )
            )

        if "exclude_revisions" in yaml_dict:
            include_revisions.difference_update(
                parse_revisions(yaml_dict["exclude_revisions"])
            )

        regression_severity: tp.Optional[int]
        if "regression_severity" in yaml_dict:
            regression_severity = yaml_dict["regression_severity"]
        else:
            regression_severity = None

        return Patch(
            project_name, shortname, description, path, include_revisions, tags,
            feature_tags, regression_severity
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

    def __hash__(self) -> int:
        hash_args = [self.shortname, self.path]
        if self.tags:
            hash_args += tuple(self.tags)
        if self.feature_tags:
            hash_args += tuple(self.feature_tags)

        return hash(tuple(hash_args))


class PatchSet:
    """A PatchSet is a storage container for project specific patches that can
    easily be accessed via the tags of a patch."""

    def __init__(self, patches: tp.Union[tp.Set[Patch], tp.FrozenSet[Patch]]):
        self.__patches: tp.FrozenSet[Patch] = frozenset(patches)

    def __iter__(self) -> tp.Iterator[Patch]:
        return self.__patches.__iter__()

    def __contains__(self, value: tp.Any) -> bool:
        return self.__patches.__contains__(value)

    def __len__(self) -> int:
        return len(self.__patches)

    def __getitem__(self, tags: tp.Union[str, tp.Iterable[str]]) -> 'PatchSet':
        """
        Overrides the bracket operator of a PatchSet.

        Returns a PatchSet, such that all patches include all the tags given
        """
        # TODO: Discuss if we really want this. Currently this is an "all_of"
        # access We could consider to remove the bracket operator and only
        # provide the all_of/any_of accessors as it would be clearer what the
        # exact behavior is

        # Trick to handle correct set construction if just a single tag is given
        if isinstance(tags, str):
            tags = [tags]

        tag_set = set(tags)
        res_set = set()

        for patch in self.__patches:
            if patch.tags and tag_set.issubset(patch.tags):
                res_set.add(patch)

        return PatchSet(res_set)

    def __and__(self, rhs: "PatchSet") -> "PatchSet":
        return PatchSet(self.__patches.intersection(rhs.__patches))

    def __or__(self, rhs: "PatchSet") -> "PatchSet":
        """Implementing the union of two sets."""
        return PatchSet(self.__patches.union(rhs.__patches))

    def any_of(self, tags: tp.Union[str, tp.Iterable[str]]) -> "PatchSet":
        """Returns a patch set with patches containing at least one of the given
        tags."""
        # Trick to handle just a single tag being passed
        if isinstance(tags, str):
            tags = [tags]

        result: tp.Set[Patch] = set()
        for patch in self:
            if patch.tags and any(tag in patch.tags for tag in tags):
                result.add(patch)

        return PatchSet(result)

    def all_of(self, tags: tp.Union[str, tp.Iterable[str]]) -> "PatchSet":
        """
        Returns a patch set with patches containing all the given tags.

        Equivalent to bracket operator (__getitem__)
        """
        return self[tags]

    def any_of_features(self, feature_tags: tp.Iterable[str]) -> "PatchSet":
        """Returns a patch set with patches containing at least one of the given
        feature tags."""
        tag_set = set(feature_tags)
        result: tp.Set[Patch] = set()
        for patch in self:
            if patch.feature_tags and patch.feature_tags.intersection(tag_set):
                result.add(patch)

        return PatchSet(result)

    def all_of_features(
        self, feature_tags: tp.Union[str, tp.Iterable[str]]
    ) -> "PatchSet":
        """Returns a patch set with patches containing all the given feature
        tags."""
        tag_set = set(feature_tags)
        result: tp.Set[Patch] = set()
        for patch in self:
            if patch.feature_tags and tag_set.issubset(patch.feature_tags):
                result.add(patch)

        return PatchSet(result)

    def __hash__(self) -> int:
        return hash(self.__patches)

    def __repr__(self) -> str:
        repr_str = ", ".join([f"{k.shortname}" for k in self.__patches])

        return f"PatchSet({{{repr_str}}})"


class PatchProvider(Provider):
    """A provider for getting patch files for a certain project."""

    patches_repository = "https://github.com/se-sic/vara-project-patches.git"

    patches_source = bb.source.Git(
        remote=patches_repository,
        local="patch-configurations",
        refspec="origin/HEAD",
        limit=None,
        shallow=False
    )

    def __init__(self, project: tp.Type[Project]):
        super().__init__(project)

        self._update_local_patches_repo()
        repo = self._get_patches_repository()

        patches_project_dir = repo.worktree_path / self.project.NAME

        if not patches_project_dir.is_dir():
            warnings.warn(
                "Could not find patches directory for project "
                f"'{self.project.NAME}'."
            )

        self.__patches: tp.Set[Patch] = set()

        # Update repository to have all upstream changes
        project_repo = get_local_project_repo(self.project.NAME)
        fetch_repository(project_repo)

        for root, _, files in os.walk(patches_project_dir):
            for filename in files:
                if not filename.endswith(".info"):
                    continue

                info_path = Path(os.path.join(root, filename))
                try:
                    current_patch = Patch.from_yaml(info_path)
                    self.__patches.add(current_patch)
                except YAMLError:
                    warnings.warn(
                        f"Unable to parse patch info in: '{filename}'"
                    )

    def get_by_shortname(self, shortname: str) -> tp.Optional[Patch]:
        """
        Returns a patch with a specific shortname, if such a patch exists.

        None otherwise
        """
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
    ) -> 'PatchProvider':
        """
        Creates a provider instance for the given project.

        Note:
            A provider may not contain any patches at all if there are no
            existing patches for a project

        Returns:
            a provider instance for the given project
        """
        return PatchProvider(project)

    @classmethod
    def create_default_provider(
        cls: tp.Type[ProviderType], project: tp.Type[Project]
    ) -> 'PatchProvider':
        """
        Creates a default provider instance that can be used with any project.

        Returns:
            a default provider instance
        """
        raise AssertionError(
            "All usages should be covered by the project specific provider."
        )

    @classmethod
    def _get_patches_repository(cls) -> RepositoryHandle:
        return RepositoryHandle(
            Path(target_prefix()) / cls.patches_source.local
        )

    @classmethod
    def _update_local_patches_repo(cls) -> None:
        lock_path = Path(target_prefix()) / "patch_provider.lock"

        with lock_file(lock_path):
            cls.patches_source.fetch()
            pull_current_branch(cls._get_patches_repository())
