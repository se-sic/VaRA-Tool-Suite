from plumbum import local

from benchbuild.utils.run import run
from benchbuild.utils.compiler import cxx
from benchbuild.utils.download import with_git
import benchbuild.project as prj


@with_git(
    "https://github.com/se-passau/vara-perf-tests.git",
    limit=1,
    refspec="origin/f-taintTests")
class TaintTests(prj.Project):  # type: ignore
    """
    Taint tests:
        Different small test files for taint propagation
    """

    NAME = 'taint-tests'
    DOMAIN = 'testing'
    GROUP = 'test_projects'

    SRC_FILE = "vara-perf-tests"

    CPP_FILES = [
        "arrayTaintPropagation.cpp",
        "byValueArgPassing.cpp",
        "coeceredReturnValuePassing.cpp",
        "coercedArgPassing.cpp",
        "controlFlowDependency.cpp",
        "operatorTaintPropagation.cpp",
        "pointerTaintPropagation1.cpp",
        "pointerTaintPropagation2.cpp",
        "pointerTaintPropagation3.cpp",
        "regularArgPassing.cpp",
        "regularReturnValuePassing.cpp",
        "returnValueMapping1.cpp",
        "returnValueMapping2.cpp",
        "switchFallthrough.cpp",
        "unionTaintPropagation.cpp",
        "variableLengthArgForwarding.cpp",
        "variableLengthArgPassing.cpp"
    ]

    BIN_NAMES =  [file_name.replace('.cpp', '') \
        for file_name in CPP_FILES]

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        clang = cxx(self)
        with local.cwd(self.SRC_FILE + "/taint-tests"):
            for file in self.CPP_FILES:
                run(clang[file, "-o", file.replace('.cpp','')])
