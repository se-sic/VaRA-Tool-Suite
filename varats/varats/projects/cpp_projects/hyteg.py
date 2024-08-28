"""Adds the HyTeg framework as a project to VaRA-TS."""
import logging
import os
import typing as tp

import benchbuild as bb
from benchbuild.command import WorkloadSet, SourceRoot
from benchbuild.utils.cmd import ninja, cmake, mkdir
from benchbuild.utils.revision_ranges import SingleRevision
from plumbum import local

from varats.experiment.workload_util import WorkloadCategory, RSBinary
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    get_local_project_repo,
    BinaryType,
    ProjectBinaryWrapper,
    RevisionBinaryMap,
)
from varats.project.sources import FeatureSource
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.utils.git_commands import update_all_submodules
from varats.utils.git_util import ShortCommitHash

LOG = logging.getLogger(__name__)


class HyTeg(VProject):
    """
    C++ framework for large scale high performance finite element simulations
    based on (but not limited to) matrix-free geometric multigrid.

    Notes:
        1.
        Currently, HyTeg CANNOT be compiled with the Phasar passes activated
        in vara. Trying to do so will crash the compiler

        If you use Dune with an experiment that uses the vara compiler,
        add `-mllvm --vara-disable-phasar` to the projects `cflags` to
        disable phasar passes.
        This will still allow to analyse compile-time variability.

        2.
        Due to the way that benchbuild generates the build folder names when
        running experiments in different configurations, HyTeg currently DOES
        NOT work out of the box when creating a case study with multiple
        configurations. This is due to benchbuild creating a temporary folder
        name with a comma in it to separate the revision and configuration
        id.
        This comma will be misinterpreted when the path for the eigen library
        is passed onto the linker.

        There is a limited workaround for this:
        1. Copy the eigen library revision that you want HyTeg to use to some
        other accessible location (That has no comma in its absolute path)
        2. Set the environment variable EIGEN_PATH to point to the absolute
        path of that directory
            - This can be achieved by either EXPORT-ing it manually, adding it
            to your .benchbuild.yml configuration or (when running with slurm)
            adding the export to your slurm scripts
    """
    NAME = 'HyTeg'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.HPC

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="HyTeg",
            remote="https://github.com/se-sic/hyteg-VaRA.git",
            local="HyTeg",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("HyTeg") / "build" / "apps" / "profiling" /
                RSBinary('ProfilingApp'),
                label='ProfilingApp'
            )
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List['ProjectBinaryWrapper']:
        binaries = RevisionBinaryMap(get_local_project_repo(HyTeg.NAME))

        binaries.specify_binary(
            "ProfilingApp",
            BinaryType.EXECUTABLE,
            only_valid_in=SingleRevision(
                "f4711dadc3f61386e6ccdc704baa783253332db2"
            )
        )

        return binaries[revision]

    def compile(self) -> None:
        """Compile HyTeg with irrelevant settings disabled."""
        hyteg_source = local.path(self.source_of(self.primary_source))

        mkdir("-p", hyteg_source / "build")

        update_all_submodules(hyteg_source, recursive=True, init=True)

        cc_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        cmake_args = [
            "-G", "Ninja", "..", "-DWALBERLA_BUILD_WITH_MPI=OFF",
            "-DHYTEG_BUILD_DOC=OFF"
        ]

        if (eigen_path := os.getenv("EIGEN_PATH")):
            cmake_args.append(f"-DEIGEN_DIR={eigen_path}")
        else:
            LOG.warning(
                "EIGEN_PATH environment variable not set! This will cause"
                " compilation errors when using configurations"
            )

        with local.cwd(hyteg_source / "build"):
            with local.env(CC=str(cc_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)(*cmake_args)

                with local.cwd(hyteg_source / "build"):
                    bb.watch(ninja)("ProfilingApp")

    def recompile(self) -> None:
        """Recompiles HyTeg e.g. after a patch has been applied."""
        hyteg_source = local.path(self.source_of(self.primary_source))

        with local.cwd(hyteg_source / "build"):
            bb.watch(ninja)("ProfilingApp")

    def run_tests(self) -> None:
        pass
