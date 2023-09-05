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
    """Simulation framework for various applications in mathematics and
    physics."""

    NAME = 'DunePerfRegression'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.CPP_LIBRARY

    SOURCE = [
        PaperConfigSpecificGit(
            project_name='DunePerfRegression',
            remote='git@github.com:se-sic/dune-VaRA.git',
            local='dune-VaRA',
            refspec='origin/f-RefactorPoissonFeature',
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

        return binary_map[revision]

    def compile(self) -> None:
        """Compile the project using the in-built tooling from dune."""
        version_source = local.path(self.source_of(self.primary_source))

        # Currently Phasar passes crash the compiler
        # This limits us to analysing compile time variability
        self.cflags += ["-mllvm", "--vara-disable-phasar"]

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

        # Currently Phasar passes crash the compiler
        # This limits us to analysing compile time variability
        self.cflags += ["-mllvm", "--vara-disable-phasar"]

        with local.env(CC=bb.compiler.cc(self), CXX=bb.compiler.cxx(self)):
            with local.cwd(version_source):
                dunecontrol = cmd['./dune-common/bin/dunecontrol']

                bb.watch(dunecontrol
                        )('--module=dune-performance-regressions', 'make')

    def run_tests(self) -> None:
        pass
