"""Collection of varats project sources that help in writing projects."""

import os
import typing as tp
from pathlib import Path

import benchbuild.source
import plumbum as pb
from benchbuild.source import Git, GitSubmodule
from benchbuild.source.base import target_prefix
from benchbuild.utils.cmd import cp, git, mkdir

from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_util import copy_renamed_git_to_dest
from varats.utils.filesystem_util import lock_file
from varats.utils.git_util import RepositoryHandle


class VaraTestRepoSubmodule(GitSubmodule):
    """A source for submodule repos stored in the vara-test-repos repository."""

    __vara_test_repos_git = Git(
        remote="https://github.com/se-sic/vara-test-repos",
        local="vara_test_repos",
        refspec="origin/HEAD",
        shallow=False,
        limit=None,
    )

    def fetch(self) -> pb.LocalPath:
        """
        Fetches the submodule.

        Overrides ``GitSubmodule`` s fetch to
          1. fetch the vara-test-repos repo
          2. extract the specified submodule from the vara-test-repos repo
          3. rename files that were made git_storable (e.g., .gitted) back to
             their original name (e.g., .git)

        Returns:
            the path where the inner repo is extracted to
        """
        self.__vara_test_repos_git.shallow = self.shallow
        self.__vara_test_repos_git.clone = self.clone

        remote = self.remote
        assert isinstance(remote, str), "Git remote must be a string."

        vara_test_repos_path = Path(self.__vara_test_repos_git.fetch())
        submodule_path = vara_test_repos_path / remote
        submodule_target = Path(target_prefix()) / self.local

        # Extract submodule
        if not submodule_target.is_dir():
            copy_renamed_git_to_dest(submodule_path, submodule_target)

        return tp.cast("pb.LocalPath", pb.local.path(submodule_target))


class VaraTestRepoSource(PaperConfigSpecificGit):
    """A source for repos stored in the vara-test-repos repository."""

    __vara_test_repos_git = Git(
        remote="https://github.com/se-sic/vara-test-repos",
        local="vara_test_repos",
        refspec="origin/HEAD",
        shallow=False,
        limit=None,
    )

    def fetch(self) -> pb.LocalPath:
        """
        Fetches the repo.

        Overrides ``Git`` s fetch to
          1. fetch the vara-test-repos repo
          2. extract the specified repo from the vara-test-repos repo
          3. rename files that were made git_storable (e.g., .gitted) back to
             their original name (e.g., .git)

        Returns:
            the path where the inner repo is extracted to
        """
        self.__vara_test_repos_git.shallow = self.shallow
        self.__vara_test_repos_git.clone = self.clone

        remote = self.remote
        assert isinstance(remote, str), "Git remote must be a string."

        vara_test_repos_path = Path(self.__vara_test_repos_git.fetch())
        main_src_path = vara_test_repos_path / remote
        main_tgt_path = Path(target_prefix()) / self.local

        # Extract main repository
        if not main_tgt_path.is_dir():
            copy_renamed_git_to_dest(main_src_path, main_tgt_path)

        return tp.cast("pb.LocalPath", pb.local.path(main_tgt_path))

    def version(self, target_dir: str, version: str = 'HEAD') -> pb.LocalPath:
        """Create a new git worktree pointing to the requested version."""
        remote = self.remote
        assert isinstance(remote, str), "Git remote must be a string."

        main_repo_src_local = self.fetch()
        tgt_loc = (
            tp.cast("pb.LocalPath", pb.local.path(target_dir)) / self.local
        )
        vara_test_repos_path = Path(self.__vara_test_repos_git.fetch())
        main_repo_src_remote = vara_test_repos_path / remote

        mkdir('-p', tgt_loc)

        # Extract main repository
        cp("-r", main_repo_src_local + "/.", tgt_loc)

        # Skip submodule extraction if none exist
        if not (tgt_loc / ".gitmodules").exists():
            with pb.local.cwd(tgt_loc):
                git("checkout", "--detach", version)
            return tgt_loc

        # Extract submodules
        with pb.local.cwd(tgt_loc):
            # Get submodule entries
            submodule_url_entry_list = git(
                "config",
                "--file",
                ".gitmodules",
                "--name-only",
                "--get-regexp",
                "url",
            ).split('\n')

            # Remove empty strings
            submodule_url_entry_list = list(
                filter(None, submodule_url_entry_list)
            )

            for entry in submodule_url_entry_list:
                relative_submodule_url = Path(
                    git(
                        "config", "--file", ".gitmodules", "--get", entry
                    ).replace('\n', '')
                )
                copy_renamed_git_to_dest(
                    main_repo_src_remote / relative_submodule_url,
                    relative_submodule_url,
                )
            git("checkout", "--detach", version)
            git("submodule", "update")

        return tgt_loc


class GitFileSource(benchbuild.source.Git):
    """
    A source to provide one or multiple files stored in a Git repository.

    From the motivation similar to the HTTPMultiple source. Common uses may be
    the use of benchmark/example workload repositories
    """

    def __init__(
        self,
        remote: str,
        local: str,
        revision: str,
        files: tp.Iterable[str],
        refspec: str = "HEAD",
    ) -> None:
        """Create a GitFileSource for `files` in the repo at `remote`."""
        # Initiate the project with the whole history
        super().__init__(
            remote, local, refspec=refspec, limit=None, shallow=False
        )
        self.__files = files
        self.__revision = revision

    @property
    def revision(self) -> str:
        """The revision from which the files are fetched."""
        return self.__revision

    def version(self, target_dir: str, version: str = "") -> pb.LocalPath:
        """
        Fetches the defined files for a given version to the target directory.

        Args:
            target_dir: directory to fetch the files into
            version: revision to fetch the files at; defaults to `revision`

        Returns:
            the path where the files were fetched to
        """
        if len(version) == 0:
            version = self.revision

        prefix = Path(benchbuild.source.base.target_prefix())
        flat_local = self.local.replace(os.sep, '-')
        file_lock = f".{flat_local}.lock"

        # Guard simultaneous access of multiple projects with the same local
        with lock_file(prefix / file_lock):
            src_loc = Path(self.fetch())
            tgt_subdir = f'{self.local}@{version}/'
            tgt_loc = tp.cast(
                "pb.LocalPath", pb.local.path(target_dir) / tgt_subdir
            )

            repo = RepositoryHandle(src_loc)

            # Check out requested version, store current head to restore later
            initial_commit = repo.pygit_repo.head
            repo("checkout", version)

            # Create target directory
            mkdir("-p", tgt_loc)
            cp = pb.local["cp"]

            with pb.local.cwd(src_loc):
                for file in self.__files:
                    flat_file = file.replace(os.sep, "-")
                    cp(file, tgt_loc / flat_file)

            repo.pygit_repo.checkout(initial_commit)

        pb.local["ln"]('-sf', tgt_loc, pb.local.path(target_dir) / self.local)

        return tgt_loc

    def versions(self) -> list[benchbuild.source.base.Variant]:
        """Return the variants matching this source's revision."""
        versions = super().versions()

        return [v for v in versions if v.version == self.__revision]
