import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make, cmake, mkdir
from benchbuild.utils.revision_ranges import SingleRevision
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import get_local_project_git_path, BinaryType
from varats.project.sources import FeatureSource
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap
from varats.utils.settings import bb_cfg


class HyTeg(VProject):
    NAME = 'HyTeg'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.CPP_LIBRARY

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="HyTeg",
            remote="git@github.com:se-sic/hyteg-VaRA.git",
            local="HyTeg",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        FeatureSource()
    ]

    WORKLOADS = {}

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List['ProjectBinaryWrapper']:
        binaries = RevisionBinaryMap(get_local_project_git_path(HyTeg.NAME))

        binaries.specify_binary(
            "build/apps/profiling/ProfilingApp",
            BinaryType.EXECUTABLE,
            only_valid_in=SingleRevision(
                "f4711dadc3f61386e6ccdc704baa783253332db2"
            )
        )

        return binaries[revision]

    def compile(self) -> None:
        hyteg_source = local.path(self.source_of(self.primary_source))

        mkdir("-p", hyteg_source / "build")

        # Currently Phasar passes crash the compiler
        # This limits us to analysing compile time variability
        self.cflags += ["-mllvm", "--vara-disable-phasar"]

        cc_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        with local.cwd(hyteg_source / "build"):
            with local.env(CC=str(cc_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)("..", "-DWALBERLA_BUILD_WITH_MPI=OFF")

                with local.cwd(hyteg_source / "build" / "apps"):
                    bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    def recompile(self) -> None:
        pass

    def run_tests(self) -> None:
        pass
