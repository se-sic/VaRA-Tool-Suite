"""Project file for Dune."""
import shutil
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.command import SourceRoot, WorkloadSet
from benchbuild.utils import cmd
from benchbuild.utils.revision_ranges import RevisionRange
from plumbum import local

from varats.containers.containers import ImageBase, get_base_image
from varats.experiment.experiment_util import ZippedReportFolder
from varats.experiment.workload_util import RSBinary, WorkloadCategory
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    BinaryType,
    ProjectBinaryWrapper,
    RevisionBinaryMap,
    get_local_project_repo,
)
from varats.project.sources import FeatureSource
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.testsuite_utils import (
    ctest_get_test_names,
    ctest_run_testsuite,
)


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
                label='dune-helloworld'
            ),
            VCommand(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson_test'),
                label='poisson-non-separated',
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
                label='poisson-ug-pk-2d',
                creates=['poisson-UG-Pk-2d.vtu']
            ),
            VCommand(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson_yasp_q1_2d'),
                label='poisson-yasp-q1-2d',
                creates=['poisson-yasp-q1-2d.vtu']
            ),
            VCommand(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson_yasp_q1_3d'),
                label='poisson-yasp-q1-3d',
                creates=['poisson-yasp-q1-3d.vtu']
            ),
            VCommand(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson_yasp_q2_2d'),
                label='poisson-yasp-q2-2d',
                creates=['poisson-yasp-q2-2d.vtu']
            ),
            VCommand(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson_yasp_q2_3d'),
                label='poisson-yasp-q2-3d',
                creates=['poisson-yasp-q2-3d.vtu']
            ),
            VCommand(
                SourceRoot(
                    "dune-VaRA/dune-performance-regressions/build-cmake/src"
                ) / RSBinary('poisson_alugrid'),
                label='poisson-alugrid',
                creates=['poisson_ALU_Pk_2d.vtu']
            )
        ]
    }

    __DUNE_MODULES = [
        "dune-common", "dune-istl", "dune-geometry", "dune-uggrid", "dune-grid",
        "dune-typetree", "dune-multidomaingrid", "dune-localfunctions",
        "dune-functions", "dune-alugrid", "dune-pdelab"
    ]

    __CMAKE_FLAGS = [
        "-DDUNE_ENABLE_PYTHONBINDINGS=OFF",
        "-DCMAKE_DISABLE_FIND_PACKAGE_MPI=TRUE",
        "-DCMAKE_DISABLE_FIND_PACKAGE_Doxygen=TRUE",
    ]

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
                CMAKE_FLAGS=" ".join(self.__CMAKE_FLAGS)
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

    # SupportsTesting interface
    def prepare_test_environment(self) -> None:
        """Prepare the testsuite for the project."""
        version_source = local.path(self.source_of(self.primary_source))
        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        with local.cwd(version_source):
            dunecontrol = cmd['./dune-common/bin/dunecontrol']

            with local.env(
                CC=c_compiler,
                CXX=cxx_compiler,
                CMAKE_FLAGS=" ".join(self.__CMAKE_FLAGS)
            ):
                bb.watch(dunecontrol["cmake"])()

    def build_tests(self) -> None:
        """Build the tests for all subprojects."""
        version_source = local.path(self.source_of(self.primary_source))

        with local.cwd(version_source):
            dunecontrol = cmd['./dune-common/bin/dunecontrol']

        for module in DunePerfRegression.__DUNE_MODULES:
            if module == "dune-pdelab":
                # skip the pdalab module as building tests fails
                continue
            bb.watch(
                dunecontrol[f"--only={module}", "bexec", "make", "build_tests"]
            )()

    def get_test_names(self) -> tp.Iterable[str]:
        """
        Get the test names for the project.

        As dune uses hierarchical project structure, test names are prefixed
        with the module name, separated by a '#'.
        """
        version_source = local.path(self.source_of(self.primary_source))

        test_list = []
        for module in DunePerfRegression.__DUNE_MODULES:
            if module == "dune-pdelab":
                # skip the pdalab module as building tests fails
                continue

            test_names = ctest_get_test_names(
                version_source / module / "build-cmake"
            )

            test_list.extend([f"{module}#{test}" for test in test_names])

        return test_list

    def run_testsuite(
        self,
        test_report_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None
    ) -> bool:
        """Run the testsuite for the project."""
        version_source = local.path(self.source_of(self.primary_source))

        tests_per_module: tp.Dict[str, tp.List[str]] = {
            module: [] for module in DunePerfRegression.__DUNE_MODULES
        }

        if tests_to_run is None:
            # In case no test names are given, we run all tests
            tests_to_run = []

        # Split the tests into their respective modules
        for test in tests_to_run:
            module, test_name = test.split("#", 1)
            if module not in tests_per_module:
                print(f"Unknown module {module} for test {test_name}.")
                continue
            tests_per_module[module].append(test_name)

        overall_result = True

        aggregated_results = self.builddir / "aggregated_test_results.zip"
        with ZippedReportFolder(aggregated_results) as zip_folder:
            for module in DunePerfRegression.__DUNE_MODULES:
                if module == "dune-pdelab":
                    # skip the pdalab module as building tests fails
                    continue

                module_test_report = Path(zip_folder) / f"{module}-tests.xml"
                module_build_dir = version_source / module / "build-cmake"
                overall_result &= ctest_run_testsuite(
                    module_build_dir, module_test_report,
                    tests_per_module[module]
                )

        if test_report_path:
            # Move the aggregated test results to the specified path
            shutil.copy(aggregated_results, test_report_path)

        return overall_result
