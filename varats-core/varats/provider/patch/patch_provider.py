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

from varats.project.project_util import get_local_project_git_path
from varats.provider.provider import Provider, ProviderType
from varats.utils.git_commands import pull_current_branch, fetch_repository
from varats.utils.git_util import (
    CommitHash,
    ShortCommitHash,
    get_all_revisions_between,
    get_initial_commit,
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
        self.valid_revisions: tp.Set[
            CommitHash] = valid_revisions if valid_revisions else set()
        self.tags: tp.Optional[tp.Set[str]] = tags

    @staticmethod
    def from_yaml(yaml_path: Path):
        """Creates a Patch from a YAML file."""

        yaml_dict = yaml.safe_load(yaml_path.read_text())

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

        project_git_path = get_local_project_git_path(project_name)

        # Update repository to have all upstream changes
        fetch_repository(project_git_path)

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
                                ShortCommitHash, project_git_path
                            )
                        )
                else:
                    res.update(
                        get_all_revisions_between(
                            rev_dict["revision_range"]["start"],
                            rev_dict["revision_range"]["end"], ShortCommitHash,
                            project_git_path
                        )
                    )

            return res

        if "include_revisions" in yaml_dict:
            include_revisions = parse_revisions(yaml_dict["include_revisions"])
        else:
            include_revisions: tp.Set[CommitHash] = set(
                get_all_revisions_between(
                    get_initial_commit(project_git_path).hash, "",
                    ShortCommitHash, project_git_path
                )
            )

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

    def __hash__(self):
        if self.tags:
            return hash((self.shortname, str(self.path), tuple(self.tags)))

        return hash((self.shortname, str(self.path)))


class PatchSet:
    """A PatchSet is a storage container for project specific patches that can
    easily be accessed via the tags of a patch."""

    def __init__(self, patches: tp.Set[Patch]):
        self.__patches: tp.FrozenSet[Patch] = frozenset(patches)

    def __iter__(self) -> tp.Iterator[Patch]:
        return self.__patches.__iter__()

    def __contains__(self, value: tp.Any) -> bool:
        return self.__patches.__contains__(value)

    def __len__(self) -> int:
        return len(self.__patches)

    def __getitem__(self, tags: tp.Union[str, tp.Iterable[str]]):
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

        # BB only performs a fetch so our repo might be out of date
        pull_current_branch(self._get_patches_repository_path())

        patches_project_dir = Path(
            self._get_patches_repository_path() / self.project.NAME
        )

        if not patches_project_dir.is_dir():
            warnings.warn(
                "Could not find patches directory for project "
                f"'{self.project.NAME}'."
            )

        self.__patches: tp.Set[Patch] = set()

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
    ):
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
    ):
        """
        Creates a default provider instance that can be used with any project.

        Returns:
            a default provider instance
        """
        raise AssertionError(
            "All usages should be covered by the project specific provider."
        )

    @classmethod
    def _get_patches_repository_path(cls) -> Path:
        cls.patches_source.fetch()

        return Path(target_prefix()) / cls.patches_source.local
