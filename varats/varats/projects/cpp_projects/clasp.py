"""Project file for clasp."""
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
    get_tagged_commits,
    ProjectBinaryWrapper,
    get_local_project_git_path,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.provider.release.release_provider import (
    ReleaseProviderHook,
    ReleaseType,
)
from varats.utils.git_util import (
    RevisionBinaryMap,
    ShortCommitHash,
    FullCommitHash,
)
from varats.utils.settings import bb_cfg


class Clasp(VProject, ReleaseProviderHook):
    """clasp is an answer set solver for (extended) normal and disjunctive logic
    programs."""

    NAME = 'clasp'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.SOLVER

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="clasp",
            remote="https://github.com/potassco/clasp.git",
            local="clasp",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Clasp.NAME))
        binary_map.specify_binary('build/bin/clasp', BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        clasp_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        mkdir("-p", clasp_source / "build")

        with local.cwd(clasp_source / "build"):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)("../")

            bb.watch(cmake)("--build", ".", "-j", get_number_of_jobs(bb_cfg()))
        with local.cwd(clasp_source):
            verify_binaries(self)

    @classmethod
    def get_release_revisions(
        cls, release_type: ReleaseType
    ) -> tp.List[tp.Tuple[FullCommitHash, str]]:
        major_release_regex = "^v?[0-9]+\\.[0-9]+\\.0$"
        minor_release_regex = "^v?[0-9]+\\.[0-9]+(\\.[1-9]+)?$"

        tagged_commits = get_tagged_commits(cls.NAME)
        if release_type == ReleaseType.MAJOR:
            return [(FullCommitHash(h), tag)
                    for h, tag in tagged_commits
                    if re.match(major_release_regex, tag)]
        return [(FullCommitHash(h), tag)
                for h, tag in tagged_commits
                if re.match(minor_release_regex, tag)]
