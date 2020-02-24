from benchbuild.utils.download import with_wget
from benchbuild.utils.run import run
from benchbuild.utils.compiler import cc
import benchbuild.project as prj


@with_wget({
    "1.0":
        "https://raw.githubusercontent.com/se-passau/" +
        "vara-perf-tests/master/examples/min-3.c"
})
class MinPerf3(prj.Project):  # type: ignore
    """ minperf 3 """

    NAME = 'minperf3'
    GROUP = 'Perf'
    DOMAIN = 'Perf'

    SRC_FILE = "min-3.c"

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        clang = cc(self)
        run(clang[self.SRC_FILE, "-o", "minperf3"])
