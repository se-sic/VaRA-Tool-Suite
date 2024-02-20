"""Project file for PicoSAT."""
import re
import typing as tp

import benchbuild as bb
from benchbuild.command import WorkloadSet, SourceRoot
from benchbuild.source import HTTP
from benchbuild.source.http import HTTPUntar
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.experiment.workload_util import RSBinary, WorkloadCategory
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    BinaryType,
    get_tagged_commits,
    ProjectBinaryWrapper,
    get_local_project_git_path,
    verify_binaries,
)
from varats.project.sources import FeatureSource
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.provider.release.release_provider import (
    ReleaseProviderHook,
    ReleaseType,
)
from varats.utils.git_util import (
    RevisionBinaryMap,
    ShortCommitHash,
    FullCommitHash,
    get_all_revisions_between,
)
from varats.utils.settings import bb_cfg


class PicoSAT(VProject, ReleaseProviderHook):
    """picoSAT is a SAT solver."""

    NAME = 'picosat'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.SOLVER

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="picosat",
            remote="https://github.com/se-sic/picoSAT-mirror",
            local="picosat",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        FeatureSource(),
        HTTP(
            local="example.cnf",
            remote={
                "1.0":
                    "https://github.com/se-sic/picoSAT-mirror/releases/"
                    "download/picoSAT-965/example.cnf"
            }
        ),
        HTTPUntar(
            local="abw-N-bcsstk07.mtx-w44.cnf",
            remote={
                "1.0":
                    "https://github.com/se-sic/picoSAT-mirror/releases/"
                    "download/picoSAT-965/abw-N-bcsstk07.mtx-w44.cnf.tar.gz"
            }
        ),
        HTTPUntar(
            local="traffic_kkb_unknown.cnf",
            remote={
                "1.0":
                    "https://github.com/se-sic/picoSAT-mirror/releases/"
                    "download/picoSAT-965/traffic_kkb_unknown.cnf.tar.gz"
            }
        ),
        HTTPUntar(
            local="UNSAT_H_instances_childsnack_p11.hddl_1.cnf",
            remote={
                "1.0":
                    "https://github.com/se-sic/picoSAT-mirror/releases/"
                    "download/picoSAT-965/"
                    "UNSAT_H_instances_childsnack_p11.hddl_1.cnf.tar.gz"
            }
        ),
        HTTPUntar(
            local="UNSAT_H_instances_childsnack_p12.hddl_1.cnf",
            remote={
                "1.0":
                    "https://github.com/se-sic/picoSAT-mirror/releases/"
                    "download/picoSAT-965/"
                    "UNSAT_H_instances_childsnack_p12.hddl_1.cnf.tar.gz"
            }
        ),
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("picosat") / RSBinary("picosat"),
                "example.cnf",
                label="example.cnf",
            )
        ],
        WorkloadSet(WorkloadCategory.SMALL): [
            VCommand(
                SourceRoot("picosat") / RSBinary("picosat"),
                "aim-100-1_6-no-1.cnf",
                label="aim-100-1-6-no-1.cnf",
            )
        ],
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("picosat") / RSBinary("picosat"),
                "traffic_kkb_unknown.cnf/traffic_kkb_unknown.cnf",
                label="traffic-kkb-unknow.cnf",
            ),
            VCommand(
                SourceRoot("picosat") / RSBinary("picosat"),
                "abw-N-bcsstk07.mtx-w44.cnf/abw-N-bcsstk07.mtx-w44.cnf",
                label="abw-N-bcsstk07.mtx-w44.cnf",
            ),
        ],
        WorkloadSet(WorkloadCategory.LARGE): [
            VCommand(
                SourceRoot("picosat") / RSBinary("picosat"),
                "UNSAT_H_instances_childsnack_p11.hddl_1.cnf/"
                "UNSAT_H_instances_childsnack_p11.hddl_1.cnf",
                label="UNSAT-H-instances-childsnack-p11.hddl-1.cnf",
            ),
            VCommand(
                SourceRoot("picosat") / RSBinary("picosat"),
                "UNSAT_H_instances_childsnack_p12.hddl_1.cnf/"
                "UNSAT_H_instances_childsnack_p12.hddl_1.cnf",
                label="UNSAT-H-instances-childsnack-p12.hddl-1.cnf",
            )
        ],
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(PicoSAT.NAME))
        binary_map.specify_binary(
            'picosat', BinaryType.EXECUTABLE, valid_exit_codes=[0, 10, 20]
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        picosat_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        with local.cwd(picosat_source):
            revisions_with_new_config_name = get_all_revisions_between(
                "33c685e82213228726364980814f0183e435de78", "", ShortCommitHash
            )
        picosat_version = ShortCommitHash(self.version_of_primary)
        if picosat_version in revisions_with_new_config_name:
            config_script_name = "./configure.sh"
        else:
            config_script_name = "./configure"

        with local.cwd(picosat_source):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(local[config_script_name])(["--trace", "--stats"])
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(picosat_source):
            verify_binaries(self)

    @classmethod
    def get_release_revisions(
        cls, release_type: ReleaseType
    ) -> tp.List[tp.Tuple[FullCommitHash, str]]:
        release_regex = "^picoSAT-[0-9]+$"

        tagged_commits = get_tagged_commits(cls.NAME)

        return [(FullCommitHash(h), tag)
                for h, tag in tagged_commits
                if re.match(release_regex, tag)]


class PicoSATLT(VProject, ReleaseProviderHook):
    """Adapted version of picoSAT that has been refactored, such that it does
    not require a field-sensitive analysis."""

    NAME = 'PicosatLT'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.SOLVER

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="PicosatLT",
            remote="https://github.com/se-sic/picoSAT-vara",
            local="PicosatLT",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        FeatureSource(),
        HTTP(
            local="example.cnf",
            remote={
                "1.0":
                    "https://github.com/se-sic/picoSAT-mirror/releases/"
                    "download/picoSAT-965/example.cnf"
            }
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

    commands = []
    configs = [
        ["--all", "-i 0", "-s 1337"],
        ["--all", "-i 1", "-s 1337"],
        ["--all", "-i 1", "-s 42"],
        ["--all", "-i 1", "-s 1"],
        ["--all", "-i 0", "-s 42"],
        ["--all", "-i 0", "-s 1"],
        ["--partial", "-i 0", "-s 1337"],
        ["--partial", "-i 1", "-s 1337"],
        ["--partial", "-i 1", "-s 42"],
        ["--partial", "-i 1", "-s 1"],
        ["--partial", "-i 0", "-s 42"],
        ["--partial", "-i 0", "-s 1"],
        ["--partial", "-v", "-i 0", "-s 1337"],
        ["--partial", "-v", "-i 1", "-s 1337"],
        ["--partial", "-v", "-i 1", "-s 42"],
        ["--partial", "-v", "-i 1", "-s 1"],
        ["--partial", "-v", "-i 0", "-s 42"],
        ["--partial", "-v", "-i 0", "-s 1"],
        ["--partial", "-f", "-i 0", "-s 1337"],
        ["--partial", "-f", "-i 1", "-s 1337"],
        ["--partial", "-f", "-i 1", "-s 42"],
        ["--partial", "-f", "-i 1", "-s 1"],
        ["--partial", "-f", "-i 0", "-s 42"],
        ["--partial", "-f", "-i 0", "-s 1"],
        ["--partial", "-n", "-i 0", "-s 1337"],
        ["--partial", "-n", "-i 1", "-s 1337"],
        ["--partial", "-n", "-i 1", "-s 42"],
        ["--partial", "-n", "-i 1", "-s 1"],
        ["--partial", "-n", "-i 0", "-s 42"],
        ["--partial", "-n", "-i 0", "-s 1"],
        ["--partial", "-t compactTraceFileName", "-i 0", "-s 1337"],
        ["--partial", "-t compactTraceFileName", "-i 1", "-s 1337"],
        ["--partial", "-t compactTraceFileName", "-i 1", "-s 42"],
        ["--partial", "-t compactTraceFileName", "-i 1", "-s 1"],
        ["--partial", "-t compactTraceFileName", "-i 0", "-s 42"],
        ["--partial", "-t compactTraceFileName", "-i 0", "-s 1"],
        ["--partial", "-T extendedTraceFileName", "-i 0", "-s 1337"],
        ["--partial", "-T extendedTraceFileName", "-i 1", "-s 1337"],
        ["--partial", "-T extendedTraceFileName", "-i 1", "-s 42"],
        ["--partial", "-T extendedTraceFileName", "-i 1", "-s 1"],
        ["--partial", "-T extendedTraceFileName", "-i 0", "-s 42"],
        ["--partial", "-T extendedTraceFileName", "-i 0", "-s 1"],
        ["--partial", "-r rupFileName", "-i 0", "-s 1337"],
        ["--partial", "-r rupFileName", "-i 1", "-s 1337"],
        ["--partial", "-r rupFileName", "-i 1", "-s 42"],
        ["--partial", "-r rupFileName", "-i 1", "-s 1"],
        ["--partial", "-r rupFileName", "-i 0", "-s 42"],
        ["--partial", "-r rupFileName", "-i 0", "-s 1"],
        ["--partial", "-c coreFileName", "-i 0", "-s 1337"],
        ["--partial", "-c coreFileName", "-i 1", "-s 1337"],
        ["--partial", "-c coreFileName", "-i 1", "-s 42"],
        ["--partial", "-c coreFileName", "-i 1", "-s 1"],
        ["--partial", "-c coreFileName", "-i 0", "-s 42"],
        ["--partial", "-c coreFileName", "-i 0", "-s 1"],
        ["--partial", "-V varFileName", "-i 0", "-s 1337"],
        ["--partial", "-V varFileName", "-i 1", "-s 1337"],
        ["--partial", "-V varFileName", "-i 1", "-s 42"],
        ["--partial", "-V varFileName", "-i 1", "-s 1"],
        ["--partial", "-V varFileName", "-i 0", "-s 42"],
        ["--partial", "-V varFileName", "-i 0", "-s 1"],
        ["--all", "-v", "-i 0", "-s 1337"],
        ["--all", "-v", "-i 1", "-s 1337"],
        ["--all", "-v", "-i 1", "-s 42"],
        ["--all", "-v", "-i 1", "-s 1"],
        ["--all", "-v", "-i 0", "-s 42"],
        ["--all", "-v", "-i 0", "-s 1"],
        ["--all", "-f", "-i 0", "-s 1337"],
        ["--all", "-f", "-i 1", "-s 1337"],
        ["--all", "-f", "-i 1", "-s 42"],
        ["--all", "-f", "-i 1", "-s 1"],
        ["--all", "-f", "-i 0", "-s 42"],
        ["--all", "-f", "-i 0", "-s 1"],
        ["--all", "-n", "-i 0", "-s 1337"],
        ["--all", "-n", "-i 1", "-s 1337"],
        ["--all", "-n", "-i 1", "-s 42"],
        ["--all", "-n", "-i 1", "-s 1"],
        ["--all", "-n", "-i 0", "-s 42"],
        ["--all", "-n", "-i 0", "-s 1"],
        ["--all", "-t compactTraceFileName", "-i 0", "-s 1337"],
        ["--all", "-t compactTraceFileName", "-i 1", "-s 1337"],
        ["--all", "-t compactTraceFileName", "-i 1", "-s 42"],
        ["--all", "-t compactTraceFileName", "-i 1", "-s 1"],
        ["--all", "-t compactTraceFileName", "-i 0", "-s 42"],
        ["--all", "-t compactTraceFileName", "-i 0", "-s 1"],
        ["--all", "-T extendedTraceFileName", "-i 0", "-s 1337"],
        ["--all", "-T extendedTraceFileName", "-i 1", "-s 1337"],
        ["--all", "-T extendedTraceFileName", "-i 1", "-s 42"],
        ["--all", "-T extendedTraceFileName", "-i 1", "-s 1"],
        ["--all", "-T extendedTraceFileName", "-i 0", "-s 42"],
        ["--all", "-T extendedTraceFileName", "-i 0", "-s 1"],
        ["--all", "-r rupFileName", "-i 0", "-s 1337"],
        ["--all", "-r rupFileName", "-i 1", "-s 1337"],
        ["--all", "-r rupFileName", "-i 1", "-s 42"],
        ["--all", "-r rupFileName", "-i 1", "-s 1"],
        ["--all", "-r rupFileName", "-i 0", "-s 42"],
        ["--all", "-r rupFileName", "-i 0", "-s 1"],
        ["--all", "-c coreFileName", "-i 0", "-s 1337"],
        ["--all", "-c coreFileName", "-i 1", "-s 1337"],
        ["--all", "-c coreFileName", "-i 1", "-s 42"],
        ["--all", "-c coreFileName", "-i 1", "-s 1"],
        ["--all", "-c coreFileName", "-i 0", "-s 42"],
        ["--all", "-c coreFileName", "-i 0", "-s 1"],
        ["--all", "-V varFileName", "-i 0", "-s 1337"],
        ["--all", "-V varFileName", "-i 1", "-s 1337"],
        ["--all", "-V varFileName", "-i 1", "-s 42"],
        ["--all", "-V varFileName", "-i 1", "-s 1"],
        ["--all", "-V varFileName", "-i 0", "-s 42"],
        ["--all", "-V varFileName", "-i 0", "-s 1"],
        ["--partial", "-v", "-f", "-i 0", "-s 1337"],
        ["--partial", "-v", "-f", "-i 1", "-s 1337"],
        ["--partial", "-v", "-f", "-i 1", "-s 42"],
        ["--partial", "-v", "-f", "-i 1", "-s 1"],
        ["--partial", "-v", "-f", "-i 0", "-s 42"],
        ["--partial", "-v", "-f", "-i 0", "-s 1"],
        ["--partial", "-v", "-n", "-i 0", "-s 1337"],
        ["--partial", "-v", "-n", "-i 1", "-s 1337"],
        ["--partial", "-v", "-n", "-i 1", "-s 42"],
        ["--partial", "-v", "-n", "-i 1", "-s 1"],
        ["--partial", "-v", "-n", "-i 0", "-s 42"],
        ["--partial", "-v", "-n", "-i 0", "-s 1"],
        ["--partial", "-v", "-t compactTraceFileName", "-i 0", "-s 1337"],
        ["--partial", "-v", "-t compactTraceFileName", "-i 1", "-s 1337"],
        ["--partial", "-v", "-t compactTraceFileName", "-i 1", "-s 42"],
        ["--partial", "-v", "-t compactTraceFileName", "-i 1", "-s 1"],
        ["--partial", "-v", "-t compactTraceFileName", "-i 0", "-s 42"],
        ["--partial", "-v", "-t compactTraceFileName", "-i 0", "-s 1"],
        ["--partial", "-v", "-T extendedTraceFileName", "-i 0", "-s 1337"],
        ["--partial", "-v", "-T extendedTraceFileName", "-i 1", "-s 1337"],
        ["--partial", "-v", "-T extendedTraceFileName", "-i 1", "-s 42"],
        ["--partial", "-v", "-T extendedTraceFileName", "-i 1", "-s 1"],
        ["--partial", "-v", "-T extendedTraceFileName", "-i 0", "-s 42"],
        ["--partial", "-v", "-T extendedTraceFileName", "-i 0", "-s 1"],
        ["--partial", "-v", "-r rupFileName", "-i 0", "-s 1337"],
        ["--partial", "-v", "-r rupFileName", "-i 1", "-s 1337"],
        ["--partial", "-v", "-r rupFileName", "-i 1", "-s 42"],
        ["--partial", "-v", "-r rupFileName", "-i 1", "-s 1"],
        ["--partial", "-v", "-r rupFileName", "-i 0", "-s 42"],
        ["--partial", "-v", "-r rupFileName", "-i 0", "-s 1"],
        ["--partial", "-v", "-c coreFileName", "-i 0", "-s 1337"],
        ["--partial", "-v", "-c coreFileName", "-i 1", "-s 1337"],
        ["--partial", "-v", "-c coreFileName", "-i 1", "-s 42"],
        ["--partial", "-v", "-c coreFileName", "-i 1", "-s 1"],
        ["--partial", "-v", "-c coreFileName", "-i 0", "-s 42"],
        ["--partial", "-v", "-c coreFileName", "-i 0", "-s 1"],
        ["--partial", "-v", "-V varFileName", "-i 0", "-s 1337"],
        ["--partial", "-v", "-V varFileName", "-i 1", "-s 1337"],
        ["--partial", "-v", "-V varFileName", "-i 1", "-s 42"],
        ["--partial", "-v", "-V varFileName", "-i 1", "-s 1"],
        ["--partial", "-v", "-V varFileName", "-i 0", "-s 42"],
        ["--partial", "-v", "-V varFileName", "-i 0", "-s 1"],
        ["--partial", "-f", "-n", "-i 0", "-s 1337"],
        ["--partial", "-f", "-n", "-i 1", "-s 1337"],
        ["--partial", "-f", "-n", "-i 1", "-s 42"],
        ["--partial", "-f", "-n", "-i 1", "-s 1"],
        ["--partial", "-f", "-n", "-i 0", "-s 42"],
        ["--partial", "-f", "-n", "-i 0", "-s 1"],
        ["--partial", "-f", "-t compactTraceFileName", "-i 0", "-s 1337"],
        ["--partial", "-f", "-t compactTraceFileName", "-i 1", "-s 1337"],
        ["--partial", "-f", "-t compactTraceFileName", "-i 1", "-s 42"],
        ["--partial", "-f", "-t compactTraceFileName", "-i 1", "-s 1"],
        ["--partial", "-f", "-t compactTraceFileName", "-i 0", "-s 42"],
        ["--partial", "-f", "-t compactTraceFileName", "-i 0", "-s 1"],
        ["--partial", "-f", "-T extendedTraceFileName", "-i 0", "-s 1337"],
        ["--partial", "-f", "-T extendedTraceFileName", "-i 1", "-s 1337"],
        ["--partial", "-f", "-T extendedTraceFileName", "-i 1", "-s 42"],
        ["--partial", "-f", "-T extendedTraceFileName", "-i 1", "-s 1"],
        ["--partial", "-f", "-T extendedTraceFileName", "-i 0", "-s 42"],
        ["--partial", "-f", "-T extendedTraceFileName", "-i 0", "-s 1"],
        ["--partial", "-f", "-r rupFileName", "-i 0", "-s 1337"],
        ["--partial", "-f", "-r rupFileName", "-i 1", "-s 1337"],
        ["--partial", "-f", "-r rupFileName", "-i 1", "-s 42"],
        ["--partial", "-f", "-r rupFileName", "-i 1", "-s 1"],
        ["--partial", "-f", "-r rupFileName", "-i 0", "-s 42"],
        ["--partial", "-f", "-r rupFileName", "-i 0", "-s 1"],
        ["--partial", "-f", "-c coreFileName", "-i 0", "-s 1337"],
        ["--partial", "-f", "-c coreFileName", "-i 1", "-s 1337"],
        ["--partial", "-f", "-c coreFileName", "-i 1", "-s 42"],
        ["--partial", "-f", "-c coreFileName", "-i 1", "-s 1"],
        ["--partial", "-f", "-c coreFileName", "-i 0", "-s 42"],
        ["--partial", "-f", "-c coreFileName", "-i 0", "-s 1"],
        ["--partial", "-f", "-V varFileName", "-i 0", "-s 1337"],
        ["--partial", "-f", "-V varFileName", "-i 1", "-s 1337"],
        ["--partial", "-f", "-V varFileName", "-i 1", "-s 42"],
        ["--partial", "-f", "-V varFileName", "-i 1", "-s 1"],
        ["--partial", "-f", "-V varFileName", "-i 0", "-s 42"],
        ["--partial", "-f", "-V varFileName", "-i 0", "-s 1"],
        ["--partial", "-n", "-t compactTraceFileName", "-i 0", "-s 1337"],
        ["--partial", "-n", "-t compactTraceFileName", "-i 1", "-s 1337"],
        ["--partial", "-n", "-t compactTraceFileName", "-i 1", "-s 42"],
        ["--partial", "-n", "-t compactTraceFileName", "-i 1", "-s 1"],
        ["--partial", "-n", "-t compactTraceFileName", "-i 0", "-s 42"],
        ["--partial", "-n", "-t compactTraceFileName", "-i 0", "-s 1"],
        ["--partial", "-n", "-T extendedTraceFileName", "-i 0", "-s 1337"],
        ["--partial", "-n", "-T extendedTraceFileName", "-i 1", "-s 1337"],
        ["--partial", "-n", "-T extendedTraceFileName", "-i 1", "-s 42"],
        ["--partial", "-n", "-T extendedTraceFileName", "-i 1", "-s 1"],
        ["--partial", "-n", "-T extendedTraceFileName", "-i 0", "-s 42"],
        ["--partial", "-n", "-T extendedTraceFileName", "-i 0", "-s 1"],
        ["--partial", "-n", "-r rupFileName", "-i 0", "-s 1337"],
        ["--partial", "-n", "-r rupFileName", "-i 1", "-s 1337"],
        ["--partial", "-n", "-r rupFileName", "-i 1", "-s 42"],
        ["--partial", "-n", "-r rupFileName", "-i 1", "-s 1"],
        ["--partial", "-n", "-r rupFileName", "-i 0", "-s 42"],
        ["--partial", "-n", "-r rupFileName", "-i 0", "-s 1"],
        ["--partial", "-n", "-c coreFileName", "-i 0", "-s 1337"],
        ["--partial", "-n", "-c coreFileName", "-i 1", "-s 1337"],
        ["--partial", "-n", "-c coreFileName", "-i 1", "-s 42"],
        ["--partial", "-n", "-c coreFileName", "-i 1", "-s 1"],
        ["--partial", "-n", "-c coreFileName", "-i 0", "-s 42"],
        ["--partial", "-n", "-c coreFileName", "-i 0", "-s 1"],
        ["--partial", "-n", "-V varFileName", "-i 0", "-s 1337"],
        ["--partial", "-n", "-V varFileName", "-i 1", "-s 1337"],
        ["--partial", "-n", "-V varFileName", "-i 1", "-s 42"],
        ["--partial", "-n", "-V varFileName", "-i 1", "-s 1"],
        ["--partial", "-n", "-V varFileName", "-i 0", "-s 42"],
        ["--partial", "-n", "-V varFileName", "-i 0", "-s 1"],
        ["--partial", "-t compactTraceFileName", "-T extendedTraceFileName", "-i 0", "-s 1337"],
        ["--partial", "-t compactTraceFileName", "-T extendedTraceFileName", "-i 1", "-s 1337"],
        ["--partial", "-t compactTraceFileName", "-T extendedTraceFileName", "-i 1", "-s 42"],
        ["--partial", "-t compactTraceFileName", "-T extendedTraceFileName", "-i 1", "-s 1"],
        ["--partial", "-t compactTraceFileName", "-T extendedTraceFileName", "-i 0", "-s 42"],
        ["--partial", "-t compactTraceFileName", "-T extendedTraceFileName", "-i 0", "-s 1"],
        ["--partial", "-t compactTraceFileName", "-r rupFileName", "-i 0", "-s 1337"],
        ["--partial", "-t compactTraceFileName", "-r rupFileName", "-i 1", "-s 1337"],
        ["--partial", "-t compactTraceFileName", "-r rupFileName", "-i 1", "-s 42"],
        ["--partial", "-t compactTraceFileName", "-r rupFileName", "-i 1", "-s 1"],
        ["--partial", "-t compactTraceFileName", "-r rupFileName", "-i 0", "-s 42"],
        ["--partial", "-t compactTraceFileName", "-r rupFileName", "-i 0", "-s 1"],
        ["--partial", "-t compactTraceFileName", "-c coreFileName", "-i 0", "-s 1337"],
        ["--partial", "-t compactTraceFileName", "-c coreFileName", "-i 1", "-s 1337"],
        ["--partial", "-t compactTraceFileName", "-c coreFileName", "-i 1", "-s 42"],
        ["--partial", "-t compactTraceFileName", "-c coreFileName", "-i 1", "-s 1"],
        ["--partial", "-t compactTraceFileName", "-c coreFileName", "-i 0", "-s 42"],
        ["--partial", "-t compactTraceFileName", "-c coreFileName", "-i 0", "-s 1"],
        ["--partial", "-t compactTraceFileName", "-V varFileName", "-i 0", "-s 1337"],
        ["--partial", "-t compactTraceFileName", "-V varFileName", "-i 1", "-s 1337"],
        ["--partial", "-t compactTraceFileName", "-V varFileName", "-i 1", "-s 42"],
        ["--partial", "-t compactTraceFileName", "-V varFileName", "-i 1", "-s 1"],
        ["--partial", "-t compactTraceFileName", "-V varFileName", "-i 0", "-s 42"],
        ["--partial", "-t compactTraceFileName", "-V varFileName", "-i 0", "-s 1"],
        ["--partial", "-T extendedTraceFileName", "-r rupFileName", "-i 0", "-s 1337"],
        ["--partial", "-T extendedTraceFileName", "-r rupFileName", "-i 1", "-s 1337"],
        ["--partial", "-T extendedTraceFileName", "-r rupFileName", "-i 1", "-s 42"],
        ["--partial", "-T extendedTraceFileName", "-r rupFileName", "-i 1", "-s 1"],
        ["--partial", "-T extendedTraceFileName", "-r rupFileName", "-i 0", "-s 42"],
        ["--partial", "-T extendedTraceFileName", "-r rupFileName", "-i 0", "-s 1"],
        ["--partial", "-T extendedTraceFileName", "-c coreFileName", "-i 0", "-s 1337"],
        ["--partial", "-T extendedTraceFileName", "-c coreFileName", "-i 1", "-s 1337"],
        ["--partial", "-T extendedTraceFileName", "-c coreFileName", "-i 1", "-s 42"],
        ["--partial", "-T extendedTraceFileName", "-c coreFileName", "-i 1", "-s 1"],
        ["--partial", "-T extendedTraceFileName", "-c coreFileName", "-i 0", "-s 42"],
        ["--partial", "-T extendedTraceFileName", "-c coreFileName", "-i 0", "-s 1"],
        ["--partial", "-T extendedTraceFileName", "-V varFileName", "-i 0", "-s 1337"],
        ["--partial", "-T extendedTraceFileName", "-V varFileName", "-i 1", "-s 1337"],
        ["--partial", "-T extendedTraceFileName", "-V varFileName", "-i 1", "-s 42"],
        ["--partial", "-T extendedTraceFileName", "-V varFileName", "-i 1", "-s 1"],
        ["--partial", "-T extendedTraceFileName", "-V varFileName", "-i 0", "-s 42"],
        ["--partial", "-T extendedTraceFileName", "-V varFileName", "-i 0", "-s 1"],
        ["--partial", "-r rupFileName", "-c coreFileName", "-i 0", "-s 1337"],
        ["--partial", "-r rupFileName", "-c coreFileName", "-i 1", "-s 1337"],
        ["--partial", "-r rupFileName", "-c coreFileName", "-i 1", "-s 42"],
        ["--partial", "-r rupFileName", "-c coreFileName", "-i 1", "-s 1"],
        ["--partial", "-r rupFileName", "-c coreFileName", "-i 0", "-s 42"],
        ["--partial", "-r rupFileName", "-c coreFileName", "-i 0", "-s 1"],
        ["--partial", "-r rupFileName", "-V varFileName", "-i 0", "-s 1337"],
        ["--partial", "-r rupFileName", "-V varFileName", "-i 1", "-s 1337"],
        ["--partial", "-r rupFileName", "-V varFileName", "-i 1", "-s 42"],
        ["--partial", "-r rupFileName", "-V varFileName", "-i 1", "-s 1"],
        ["--partial", "-r rupFileName", "-V varFileName", "-i 0", "-s 42"],
        ["--partial", "-r rupFileName", "-V varFileName", "-i 0", "-s 1"],
        ["--partial", "-c coreFileName", "-V varFileName", "-i 0", "-s 1337"],
        ["--partial", "-c coreFileName", "-V varFileName", "-i 1", "-s 1337"],
        ["--partial", "-c coreFileName", "-V varFileName", "-i 1", "-s 42"],
        ["--partial", "-c coreFileName", "-V varFileName", "-i 1", "-s 1"],
        ["--partial", "-c coreFileName", "-V varFileName", "-i 0", "-s 42"],
        ["--partial", "-c coreFileName", "-V varFileName", "-i 0", "-s 1"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 1337"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 1337"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 42"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 1"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 42"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 1"],
        ["--partial", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 1337"],
        ["--partial", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 1337"],
        ["--partial", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 42"],
        ["--partial", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 1"],
        ["--partial", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 42"],
        ["--partial", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 1"],
        ["--all", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 1337"],
        ["--all", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 1337"],
        ["--all", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 42"],
        ["--all", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 1"],
        ["--all", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 42"],
        ["--all", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 1"],
        ["--all", "-v", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 1337"],
        ["--all", "-v", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 1337"],
        ["--all", "-v", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 42"],
        ["--all", "-v", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 1"],
        ["--all", "-v", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 42"],
        ["--all", "-v", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 1"],
        ["--all", "-v", "-f", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 1337"],
        ["--all", "-v", "-f", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 1337"],
        ["--all", "-v", "-f", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 42"],
        ["--all", "-v", "-f", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 1"],
        ["--all", "-v", "-f", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 42"],
        ["--all", "-v", "-f", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 1"],
        ["--all", "-v", "-f", "-n", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 1337"],
        ["--all", "-v", "-f", "-n", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 1337"],
        ["--all", "-v", "-f", "-n", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 42"],
        ["--all", "-v", "-f", "-n", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 1"],
        ["--all", "-v", "-f", "-n", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 42"],
        ["--all", "-v", "-f", "-n", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 1"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 1337"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 1337"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 42"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 1"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 42"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-r rupFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 1"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 1337"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 1337"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 42"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-c coreFileName", "-V varFileName", "-i 1", "-s 1"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 42"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-c coreFileName", "-V varFileName", "-i 0", "-s 1"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-V varFileName", "-i 0", "-s 1337"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-V varFileName", "-i 1", "-s 1337"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-V varFileName", "-i 1", "-s 42"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-V varFileName", "-i 1", "-s 1"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-V varFileName", "-i 0", "-s 42"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-V varFileName", "-i 0", "-s 1"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-i 0", "-s 1337"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-i 1", "-s 1337"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-i 1", "-s 42"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-i 1", "-s 1"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-i 0", "-s 42"],
        ["--all", "-v", "-f", "-n", "-t compactTraceFileName", "-T extendedTraceFileName", "-r rupFileName", "-c coreFileName", "-i 0", "-s 1"]
    ]

    compactTraceFileName = "compactTrace"
    extendedTraceFileName = "extendedTrace"
    rupFileName = "rupFile"
    coreFileName = "coreFile"
    varFileName = "varFile"

    for i, config in enumerate(configs):
        for i in range(1, 200):
            name = "uf50-0" + str(i)
            commands.append(VCommand(
                    SourceRoot("PicosatLT") / RSBinary("picosat"),
                    "--keep",
                    *config,
                    "uf50-218/" + name + ".cnf",
                    label=name + ' '.join(config),
                ))
        
        for i in range(1, 100):
            name = "uf250-0" + str(i)
            commands.append(VCommand(
                    SourceRoot("PicosatLT") / RSBinary("picosat"),
                    "--keep",
                    *config,
                    "uf250-1065/ai/hoos/Shortcuts/UF250.1065.100/" + name + ".cnf",
                    label=name + ' '.join(config),
                ))
            
        for i in range(1, 100):
            name = "uf150-0" + str(i)
            commands.append(VCommand(
                    SourceRoot("PicosatLT") / RSBinary("picosat"),
                    "--keep",
                    *config,
                    "uf150-1065/ai/hoos/Research/SAT/Formulae/UF150.645.100/" + name + ".cnf",
                    label=name + ' '.join(config),
                ))

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("PicosatLT") / RSBinary("picosat"),
                *["--all", "-v", "-f", "-n", "-r rupFileName", "-c coreFileName", "-i 0", "-s 1"],
                "-t compactTraceFileName",
                "-T extendedTraceFileName",
                "example.cnf",
                label="example.cnf",
            )
        ],
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("PicosatLT") / RSBinary("picosat"),
                "abw-N-bcsstk07.mtx-w44.cnf/abw-N-bcsstk07.mtx-w44.cnf",
                label="abw-N-bcsstk07.mtx-w44.cnf",
            ),
        ],
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(PicoSATLT.NAME)
        )
        binary_map.specify_binary(
            'picosat', BinaryType.EXECUTABLE, valid_exit_codes=[0, 10, 20]
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        picosat_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        with local.cwd(picosat_source):
            revisions_with_new_config_name = get_all_revisions_between(
                "33c685e82213228726364980814f0183e435de78", "", ShortCommitHash
            )
        picosat_version = ShortCommitHash(self.version_of_primary)
        if picosat_version in revisions_with_new_config_name:
            config_script_name = "./configure.sh"
        else:
            config_script_name = "./configure"

        with local.cwd(picosat_source):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(local[config_script_name])(["--trace", "--stats"])
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(picosat_source):
            verify_binaries(self)

    def recompile(self) -> None:
        """Re-Compile the project."""
        picosat_source = local.path(self.source_of(self.primary_source))
        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        with local.cwd(picosat_source):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(picosat_source):
            verify_binaries(self)

    @classmethod
    def get_release_revisions(
        cls, release_type: ReleaseType
    ) -> tp.List[tp.Tuple[FullCommitHash, str]]:
        release_regex = "^picoSAT-[0-9]+$"

        tagged_commits = get_tagged_commits(cls.NAME)

        return [(FullCommitHash(h), tag)
                for h, tag in tagged_commits
                if re.match(release_regex, tag)]
