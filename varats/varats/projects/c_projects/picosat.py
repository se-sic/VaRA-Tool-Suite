"""Project file for PicoSAT."""
import re
import typing as tp

import benchbuild as bb
from benchbuild.command import WorkloadSet, Command, SourceRoot
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
            Command(
                SourceRoot("picosat") / RSBinary("picosat"),
                "example.cnf",
                label="example.cnf",
            )
        ],
        WorkloadSet(WorkloadCategory.SMALL): [
            Command(
                SourceRoot("picosat") / RSBinary("picosat"),
                "aim-100-1_6-no-1.cnf",
                label="aim-100-1-6-no-1.cnf",
            )
        ],
        WorkloadSet(WorkloadCategory.MEDIUM): [
            Command(
                SourceRoot("picosat") / RSBinary("picosat"),
                "traffic_kkb_unknown.cnf/traffic_kkb_unknown.cnf",
                label="traffic-kkb-unknow.cnf",
            ),
            Command(
                SourceRoot("picosat") / RSBinary("picosat"),
                "abw-N-bcsstk07.mtx-w44.cnf/abw-N-bcsstk07.mtx-w44.cnf",
                label="abw-N-bcsstk07.mtx-w44.cnf",
            ),
        ],
        WorkloadSet(WorkloadCategory.LARGE): [
            Command(
                SourceRoot("picosat") / RSBinary("picosat"),
                "UNSAT_H_instances_childsnack_p11.hddl_1.cnf/"
                "UNSAT_H_instances_childsnack_p11.hddl_1.cnf",
                label="UNSAT-H-instances-childsnack-p11.hddl-1.cnf",
            ),
            Command(
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
