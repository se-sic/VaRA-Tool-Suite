"""Compile a collection of representing examples for the taint analysis."""
import typing as tp

import benchbuild as bb
from plumbum import local

from varats.utils.project_util import (
    wrap_paths_to_binaries,
    ProjectBinaryWrapper,
    BinaryType,
)


class TaintTests(bb.Project):  # type: ignore
    """
    Taint tests:

    Different small test files for taint propagation
    """

    NAME = 'taint-tests'
    GROUP = 'test_projects'
    DOMAIN = 'testing'

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-passau/vara-perf-tests.git",
            local="taint-tests",
            limit=1,
            refspec="origin/f-taintTests"
        )
    ]

    CPP_FILES = [
        "arrayTaintPropagation.cpp", "byValueArgPassing.cpp",
        "coercedArgPassing.cpp", "coercedReturnValuePassing.cpp",
        "controlFlowDependency.cpp", "operatorTaintPropagation.cpp",
        "pointerTaintPropagation1.cpp", "pointerTaintPropagation2.cpp",
        "pointerTaintPropagation3.cpp", "regularArgPassing.cpp",
        "regularReturnValuePassing.cpp", "returnValueMapping.cpp",
        "switchFallthrough.cpp", "unionTaintPropagation.cpp",
        "variableLengthArgForwarding.cpp", "variableLengthArgPassing.cpp"
    ]

    @property
    def binaries(self) -> tp.List[ProjectBinaryWrapper]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries([
            (file_name.replace('.cpp', ''), BinaryType.executable)
            for file_name in self.CPP_FILES
        ])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        source = local.path(self.source_of_primary)

        clang = bb.compiler.cxx(self)
        with local.cwd(source):
            for file in self.CPP_FILES:
                bb.watch(clang)(
                    "{name}/{file}".format(name=self.NAME, file=file), "-o",
                    file.replace('.cpp', '')
                )
