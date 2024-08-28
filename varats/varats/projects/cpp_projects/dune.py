"""Project file for Dune."""
import typing as tp

import benchbuild as bb
from benchbuild.command import WorkloadSet, SourceRoot
from benchbuild.utils import cmd
from benchbuild.utils.revision_ranges import RevisionRange
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.experiment.workload_util import RSBinary, WorkloadCategory
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
from varats.utils.git_util import ShortCommitHash


class DunePerfRegression(VProject):
    """
    Simulation framework for various applications in mathematics and physics.

    Note:
        Currently Dune CANNOT be compiled with the Phasar passes activated
        in vara.
        Trying to do so will crash the compiler

        If you use Dune with an experiment that uses the vara compiler,
        add `-mllvm --vara-disable-phasar` to the projects `cflags` to
        disable phasar passes.
         This will still allow to analyse compile-time variability.

        Might need deps:
            * klu
            * spqr
            * umfpack
            * eigen3
    """

    NAME = 'DunePerfRegression'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.CPP_LIBRARY

    SOURCE = [
        PaperConfigSpecificGit(
            project_name='DunePerfRegression',
            remote='https://github.com/se-sic/dune-VaRA.git',
            local='dune-VaRA',
            refspec='origin/HEAD',
            limit=None,
            shallow=False
        ),
        FeatureSource()
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10)

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('dune_performance_regressions'),
                label='dune_helloworld'
            ),
            VCommand(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson_test'),
                label='poisson_non_separated',
                creates=[
                    'poisson_UG_Pk_2d.vtu', 'poisson-yasp-Q1-2d.vtu',
                    'poisson-yasp-Q1-3d.vtu', 'poisson-yasp-Q2-2d.vtu',
                    'poisson-yasp-Q2-3d.vtu'
                ]
            ),
            VCommand(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson_ug_pk_2d'),
                label='poisson_ug_pk_2d',
                creates=['poisson-UG-Pk-2d.vtu']
            ),
            VCommand(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson_yasp_q1_2d'),
                label='poisson_yasp_q1_2d',
                creates=['poisson-yasp-q1-2d.vtu']
            ),
            VCommand(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson_yasp_q1_3d'),
                label='poisson_yasp_q1_3d',
                creates=['poisson-yasp-q1-3d.vtu']
            ),
            VCommand(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson_yasp_q2_2d'),
                label='poisson_yasp_q2_2d',
                creates=['poisson-yasp-q2-2d.vtu']
            ),
            VCommand(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson_yasp_q2_3d'),
                label='poisson_yasp_q2_3d',
                creates=['poisson-yasp-q2-3d.vtu']
            ),
            VCommand(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson_alugrid'),
                label='poisson_alugrid',
                creates=['poisson_ALU_Pk_2d.vtu']
            )
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List['ProjectBinaryWrapper']:
        binary_map = RevisionBinaryMap(
            get_local_project_repo(DunePerfRegression.NAME)
        )

        rev_range = RevisionRange(
            '332a9af0b7e3336dd72c4f4b74e09df525b6db0d', 'main'
        )

        binary_map.specify_binary(
            'dune_performance_regressions',
            BinaryType.EXECUTABLE,
            only_valid_in=rev_range
        )

        binary_map.specify_binary(
            'poisson_test', BinaryType.EXECUTABLE, only_valid_in=rev_range
        )

        binary_map.specify_binary(
            'poisson_alberta', BinaryType.EXECUTABLE, only_valid_in=rev_range
        )

        binary_map.specify_binary(
            'poisson_ug_pk_2d', BinaryType.EXECUTABLE, only_valid_in=rev_range
        )

        binary_map.specify_binary(
            'poisson_yasp_q1_2d',
            BinaryType.EXECUTABLE,
            only_valid_in=rev_range
        )

        binary_map.specify_binary(
            'poisson_yasp_q2_3d',
            BinaryType.EXECUTABLE,
            only_valid_in=rev_range
        )

        binary_map.specify_binary(
            'poisson_yasp_q2_2d',
            BinaryType.EXECUTABLE,
            only_valid_in=rev_range
        )

        binary_map.specify_binary(
            'poisson_yasp_q1_3d',
            BinaryType.EXECUTABLE,
            only_valid_in=rev_range
        )

        binary_map.specify_binary(
            'poisson_alugrid', BinaryType.EXECUTABLE, only_valid_in=rev_range
        )

        return binary_map[revision]

    def compile(self) -> None:
        """Compile the project using the in-built tooling from dune."""
        version_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        with local.cwd(version_source):
            with local.env(
                CC=c_compiler,
                CXX=cxx_compiler,
                CMAKE_FLAGS=" ".join([
                    "-DDUNE_ENABLE_PYTHONBINDINGS=OFF",
                    "-DCMAKE_DISABLE_FIND_PACKAGE_MPI=TRUE"
                ])
            ):
                dunecontrol = cmd['./dune-common/bin/dunecontrol']

                bb.watch(dunecontrol
                        )('--module=dune-performance-regressions', 'all')

    def recompile(self) -> None:
        """Recompiles Dune after e.g. a Patch has been applied."""
        version_source = local.path(self.source_of(self.primary_source))

        with local.cwd(version_source):
            dunecontrol = cmd['./dune-common/bin/dunecontrol']

            bb.watch(dunecontrol
                    )('--module=dune-performance-regressions', 'make')

    def run_tests(self) -> None:
        pass
