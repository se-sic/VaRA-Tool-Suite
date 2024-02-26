"""Project file for Z3."""
import re
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.utils.cmd import cmake
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from benchbuild.source.http import HTTPUntar
from varats.experiment.workload_util import RSBinary, WorkloadCategory
from benchbuild.command import WorkloadSet, Command, SourceRoot
from varats.project.project_util import (
    BinaryType,
    ProjectBinaryWrapper,
    get_local_project_git_path,
    verify_binaries,
    get_tagged_commits,
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


class Z3(VProject, ReleaseProviderHook):
    """Z3 is a theorem prover from Microsoft Research."""

    NAME = 'z3'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.SOLVER

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="z3",
            remote="https://github.com/Z3Prover/z3.git",
            local="z3",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        HTTPUntar(
            local="uf50-218",
            remote={
                "1.0":
                    "https://www.cs.ubc.ca/~hoos/SATLIB/Benchmarks/SAT/RND3SAT/uf50-218.tar.gz"
            }
        ),
        HTTPUntar(
            local="uf250-1065",
            remote={
                "2.0":
                    "https://www.cs.ubc.ca/~hoos/SATLIB/Benchmarks/SAT/RND3SAT/uf250-1065.tar.gz"
            }
        ),
        HTTPUntar(
            local="uf150-645",
            remote={
                "3.0":
                    "https://www.cs.ubc.ca/~hoos/SATLIB/Benchmarks/SAT/RND3SAT/uf150-645.tar.gz"
            }
        ),
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10)

    commands = []

    for i in range(1, 200):
        name = "uf50-0" + str(i)
        commands.append(Command(
                SourceRoot("z3") / RSBinary("z3"),
                "--keep",
                "uf50-218/" + name + ".cnf",
                label=name,
            ))
    
    for i in range(1, 100):
        name = "uf250-0" + str(i)
        commands.append(Command(
                SourceRoot("z3") / RSBinary("z3"),
                "--keep",
                "uf250-1065/ai/hoos/Shortcuts/UF250.1065.100/" + name + ".cnf",
                label=name,
            ))
        
    for i in range(1, 100):
        name = "uf150-0" + str(i)
        commands.append(Command(
                SourceRoot("z3") / RSBinary("z3"),
                "--keep",
                "uf150-1065/ai/hoos/Research/SAT/Formulae/UF150.645.100/" + name + ".cnf",
                label=name,
            ))

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Z3.NAME))
        binary_map.specify_binary('build/z3', BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        z3_source = Path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        (z3_source / "build").mkdir(parents=True, exist_ok=True)

        with local.cwd(z3_source / "build"):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "../")

            bb.watch(cmake)("--build", ".", "-j", get_number_of_jobs(bb_cfg()))
        with local.cwd(z3_source):
            verify_binaries(self)

    @classmethod
    def get_release_revisions(
        cls, release_type: ReleaseType
    ) -> tp.List[tp.Tuple[FullCommitHash, str]]:
        major_release_regex = "^(z|Z)3-[0-9]+\\.[0-9]+\\.0$"
        minor_release_regex = "^(z|Z)3-[0-9]+\\.[0-9]+(\\.[1-9]+)?$"

        tagged_commits = get_tagged_commits(cls.NAME)
        if release_type == ReleaseType.MAJOR:
            return [(FullCommitHash(h), tag)
                    for h, tag in tagged_commits
                    if re.match(major_release_regex, tag)]
        return [(FullCommitHash(h), tag)
                for h, tag in tagged_commits
                if re.match(minor_release_regex, tag)]