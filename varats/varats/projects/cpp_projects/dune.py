"""Project file for Dune."""
import typing as tp

import benchbuild as bb
from benchbuild.command import WorkloadSet, Command, SourceRoot
from benchbuild.utils import cmd
from benchbuild.utils.revision_ranges import RevisionRange
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.experiment.workload_util import RSBinary, WorkloadCategory
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    get_local_project_git_path,
    BinaryType,
    ProjectBinaryWrapper,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap


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
    """

    NAME = 'DunePerfRegression'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.CPP_LIBRARY

    SOURCE = [
        PaperConfigSpecificGit(
            project_name='DunePerfRegression',
            remote='git@github.com:se-sic/dune-VaRA.git',
            local='dune-VaRA',
            refspec='origin/HEAD',
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10)

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            Command(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('dune-performance-regressions'),
                label='dune-helloworld'
            ),
            Command(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson-test'),
                label='poisson-non-separated',
                creates=[
                    'poisson_UG_Pk_2d.vtu', 'poisson-yasp-Q1-2d.vtu',
                    'poisson-yasp-Q1-3d.vtu', 'poisson-yasp-Q2-2d.vtu',
                    'poisson-yasp-Q2-3d.vtu'
                ]
            ),
            Command(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson-ug-pk-2d'),
                label='poisson-ug-pk-2d',
                creates=['poisson-UG-Pk-2d.vtu']
            ),
            Command(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson-yasp-q1-2d'),
                label='poisson-yasp-q1-2d',
                creates=['poisson-yasp-q1-2d.vtu']
            ),
            Command(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson-yasp-q1-3d'),
                label='poisson-yasp-q1-3d',
                creates=['poisson-yasp-q1-3d.vtu']
            ),
            Command(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson-yasp-q2-2d'),
                label='poisson-yasp-q2-2d',
                creates=['poisson-yasp-q2-2d.vtu']
            ),
            Command(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson-yasp-q2-3d'),
                label='poisson-yasp-q2-3d',
                creates=['poisson-yasp-q2-3d.vtu']
            ),
            Command(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('dune_performance_regressions'),
                label='dune_helloworld'
            ),
            Command(
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
            Command(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson_ug_pk_2d'),
                label='poisson_ug_pk_2d',
                creates=['poisson-UG-Pk-2d.vtu']
            ),
            Command(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson_yasp_q1_2d'),
                label='poisson_yasp_q1_2d',
                creates=['poisson-yasp-q1-2d.vtu']
            ),
            Command(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson_yasp_q1_3d'),
                label='poisson_yasp_q1_3d',
                creates=['poisson-yasp-q1-3d.vtu']
            ),
            Command(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson_yasp_q2_2d'),
                label='poisson_yasp_q2_2d',
                creates=['poisson-yasp-q2-2d.vtu']
            ),
            Command(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson_yasp_q2_3d'),
                label='poisson_yasp_q2_3d',
                creates=['poisson-yasp-q2-3d.vtu']
            )
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List['ProjectBinaryWrapper']:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(DunePerfRegression.NAME)
        )

        binary_map.specify_binary(
            'dune-performance-regressions', BinaryType.EXECUTABLE
        )

        binary_map.specify_binary(
            'poisson-test',
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange(
                '0d02b7b9acddfc57c3a0c905d6374fabbcaa0f58', 'main'
            )
        )

        separated_poisson_range = RevisionRange(
            '97fecde34910ba1f81c988ac2e1331aecddada06', 'main'
        )

        binary_map.specify_binary(
            'poisson-alberta',
            BinaryType.EXECUTABLE,
            only_valid_in=separated_poisson_range
        )

        binary_map.specify_binary(
            'poisson-ug-pk-2d',
            BinaryType.EXECUTABLE,
            only_valid_in=separated_poisson_range
        )

        binary_map.specify_binary(
            'poisson-yasp-q1-2d',
            BinaryType.EXECUTABLE,
            only_valid_in=separated_poisson_range
        )

        binary_map.specify_binary(
            'poisson-yasp-q2-3d',
            BinaryType.EXECUTABLE,
            only_valid_in=separated_poisson_range
        )

        binary_map.specify_binary(
            'poisson-yasp-q2-2d',
            BinaryType.EXECUTABLE,
            only_valid_in=separated_poisson_range
        )

        binary_map.specify_binary(
            'poisson-yasp-q1-3d',
            BinaryType.EXECUTABLE,
            only_valid_in=separated_poisson_range
        )

        new_binary_naming_range = RevisionRange(
            '332a9af0b7e3336dd72c4f4b74e09df525b6db0d', 'main'
        )

        binary_map.specify_binary(
            'dune_performance_regressions',
            BinaryType.EXECUTABLE,
            only_valid_in=new_binary_naming_range
        )

        binary_map.specify_binary(
            'poisson_test',
            BinaryType.EXECUTABLE,
            only_valid_in=new_binary_naming_range
        )

        binary_map.specify_binary(
            'poisson_alberta',
            BinaryType.EXECUTABLE,
            only_valid_in=new_binary_naming_range
        )

        binary_map.specify_binary(
            'poisson_ug_pk_2d',
            BinaryType.EXECUTABLE,
            only_valid_in=new_binary_naming_range
        )

        binary_map.specify_binary(
            'poisson_yasp_q1_2d',
            BinaryType.EXECUTABLE,
            only_valid_in=new_binary_naming_range
        )

        binary_map.specify_binary(
            'poisson_yasp_q2_3d',
            BinaryType.EXECUTABLE,
            only_valid_in=new_binary_naming_range
        )

        binary_map.specify_binary(
            'poisson_yasp_q2_2d',
            BinaryType.EXECUTABLE,
            only_valid_in=new_binary_naming_range
        )

        binary_map.specify_binary(
            'poisson_yasp_q1_3d',
            BinaryType.EXECUTABLE,
            only_valid_in=new_binary_naming_range
        )

        return binary_map[revision]

    def compile(self) -> None:
        """Compile the project using the in-built tooling from dune."""
        version_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        with local.cwd(version_source):
            with local.env(CC=c_compiler, CXX=cxx_compiler):
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
