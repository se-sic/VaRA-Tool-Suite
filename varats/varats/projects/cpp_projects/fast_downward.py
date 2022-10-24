"""Project file for fast_downward."""
import re
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import cmake, mkdir
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper_mgmt.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    BinaryType,
    ProjectBinaryWrapper,
    get_local_project_git_path,
    get_tagged_commits,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.provider.release.release_provider import (
    ReleaseProviderHook,
    ReleaseType,
)
from varats.utils.git_util import (
    FullCommitHash,
    RevisionBinaryMap,
    ShortCommitHash,
)
from varats.utils.settings import bb_cfg


class FastDownward(VProject, ReleaseProviderHook):
    """Planning tool FastDownward (fetched by Git)"""

    NAME = 'fast_downward'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.PLANNING

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="fast_downward",
            remote="https://github.com/aibasel/downward.git",
            local="fast_downward",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(FastDownward.NAME)
        )
        binary_map.specify_binary('build/bin/downward', BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        version_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        mkdir("-p", version_source / "build")

        with local.cwd(version_source / "build"):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)("../src")

            bb.watch(cmake)("--build", ".", "-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(version_source):
            verify_binaries(self)

    @classmethod
    def get_release_revisions(
        cls, release_type: ReleaseType
    ) -> tp.List[tp.Tuple[FullCommitHash, str]]:
        repo_loc = get_local_project_git_path(cls.NAME)
        with local.cwd(repo_loc):
            # Before 2019_07, there were no real releases, but the following
            # commits were identified as suitable.
            release_commits = {
                (
                    FullCommitHash('e4eb64c613ae34b97ab9409deac5331ec2ce5e43'),
                    'release-16.07.0'
                ),
                (
                    FullCommitHash('91f44fa59ea57014a7769062a92aa752f503128e'),
                    'release-17.01.0'
                ),
                (
                    FullCommitHash('363e2fc9a8b7adb48b4c30e929097798928c7370'),
                    'release-17.07.0'
                ),
                (
                    FullCommitHash('0e8acd2f2613e032040dc6b6d4bf1926848aa4cb'),
                    'release-18.01.0'
                ),
                (
                    FullCommitHash('dd7ddfeea72a699d381dce35657d683259be77c0'),
                    'release-18.07.0'
                ),
                (
                    FullCommitHash('2cc2a66e8073a73571e0a37cd806380f13751a7c'),
                    'release-19.01.0'
                )
            }

            tagged_commits = get_tagged_commits(cls.NAME)
            release_commits = release_commits.union({
                (FullCommitHash(h), tag)
                for h, tag in tagged_commits
                if re.match("^release-[0-9]+\\.[0-9]+\\.[0-9]+$", tag)
            })

            return list(release_commits)
