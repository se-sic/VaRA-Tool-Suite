from plumbum import local

from benchbuild.utils.run import run
from benchbuild.utils.compiler import cxx
from benchbuild.utils.download import with_git
import benchbuild.project as prj


@with_git(
    "https://github.com/se-passau/vara-perf-tests.git",
    limit=1,
    refspec="HEAD")
class TaintTests(prj.Project):  # type: ignore
    """
    Taint tests:
        Different small test files for taint propagation
    """

    NAME = 'taint-tests'
    DOMAIN = 'testing'
    GROUP = 'test_projects'

    SRC_FILE = "vara-perf-tests"

    test_files = [
        "arrayTaintPropagation.cpp", "controlFlowDependency.cpp"
    ]

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        clang = cxx(self)
        with local.cwd(self.SRC_FILE + "/taint-tests"):
            for test_file in self.test_files:
                run(clang[test_file,
                          "-w -fvara-handleRM=Commit -S -emit-llvm -o",
                          test_file.replace('.cpp', '.ll')])
