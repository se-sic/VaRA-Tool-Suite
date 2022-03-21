"""Collection of special varats project sources that help in writing
projects."""

import os
from pathlib import Path

import plumbum as pb
from benchbuild.source import Git, GitSubmodule
from benchbuild.source.base import target_prefix
from benchbuild.utils.cmd import git, mkdir, cp
from plumbum import local

from varats.paper_mgmt.paper_config import PaperConfigSpecificGit
from varats.project.project_util import copy_renamed_git_to_dest


class VaraTestRepoSubmodule(GitSubmodule):  # type: ignore
    """A project source for submodule repositories stored in the vara-test-repos
    repository."""

    __vara_test_repos_git = Git(
        remote="https://github.com/se-sic/vara-test-repos",
        local="vara_test_repos",
        refspec="origin/HEAD",
        shallow=False,
        limit=None
    )

    def fetch(self) -> pb.LocalPath:
        """
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

        vara_test_repos_path = self.__vara_test_repos_git.fetch()
        submodule_path = vara_test_repos_path / Path(self.remote)
        submodule_target = local.path(target_prefix()) / Path(self.local)

        # Extract submodule
        if not os.path.isdir(submodule_target):
            copy_renamed_git_to_dest(submodule_path, submodule_target)

        return submodule_target


class VaraTestRepoSource(PaperConfigSpecificGit):
    """A project source for repositories stored in the vara-test-repos
    repository."""

    __vara_test_repos_git = Git(
        remote="https://github.com/se-sic/vara-test-repos",
        local="vara_test_repos",
        refspec="origin/HEAD",
        shallow=False,
        limit=None
    )

    def fetch(self) -> pb.LocalPath:
        """
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

        vara_test_repos_path = self.__vara_test_repos_git.fetch()
        main_src_path = vara_test_repos_path / self.remote
        main_tgt_path = local.path(target_prefix()) / self.local

        # Extract main repository
        if not os.path.isdir(main_tgt_path):
            copy_renamed_git_to_dest(main_src_path, main_tgt_path)

        return main_tgt_path

    def version(self, target_dir: str, version: str = 'HEAD') -> pb.LocalPath:
        """Overrides ``Git`` s version to create a new git worktree pointing to
        the requested version."""

        main_repo_src_local = self.fetch()
        tgt_loc = pb.local.path(target_dir) / self.local
        vara_test_repos_path = self.__vara_test_repos_git.fetch()
        main_repo_src_remote = vara_test_repos_path / self.remote

        mkdir('-p', tgt_loc)

        # Extract main repository
        cp("-r", main_repo_src_local + "/.", tgt_loc)

        # Skip submodule extraction if none exist
        if not Path(tgt_loc / ".gitmodules").exists():
            with pb.local.cwd(tgt_loc):
                git("checkout", "--detach", version)
            return tgt_loc

        # Extract submodules
        with pb.local.cwd(tgt_loc):

            # Get submodule entries
            submodule_url_entry_list = git(
                "config", "--file", ".gitmodules", "--name-only",
                "--get-regexp", "url"
            ).split('\n')

            # Remove empty strings
            submodule_url_entry_list = list(
                filter(None, submodule_url_entry_list)
            )

            for entry in submodule_url_entry_list:
                relative_submodule_url = Path(
                    git("config", "--file", ".gitmodules", "--get",
                        entry).replace('\n', '')
                )
                copy_renamed_git_to_dest(
                    main_repo_src_remote / relative_submodule_url,
                    relative_submodule_url
                )
            git("checkout", "--detach", version)
            git("submodule", "update")

        return tgt_loc
