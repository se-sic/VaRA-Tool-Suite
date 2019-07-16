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

    BIN_NAMES = [
        "arrayTaintPropagation", "pointerTaintPropagation1", "returnValueMapping2",
        "byValueArgPassing", "pointerTaintPropagation2", "switchFallthrough",
        "coeceredReturnValuePassing", "pointerTaintPropagation3", "unionTaintPropagation",
        "coercedArgPassing", "regularArgPassing", "variableLengthArgForwarding",
        "controlFlowDependency", "regularReturnValuePassing", "variableLengthArgPassing",
        "operatorTaintPropagation", "returnValueMapping1"
    ]

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        clang = cxx(self)
        with local.cwd(self.SRC_FILE + "/taint-tests"):
            for binary in self.BIN_NAMES:
                run(clang[binary + ".cpp", "-o", binary])
