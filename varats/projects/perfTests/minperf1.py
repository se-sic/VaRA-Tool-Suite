from benchbuild.utils.download import with_wget
from benchbuild.utils.run import run
from benchbuild.utils.compiler import cc
import benchbuild.project as prj


@with_wget({"1.0": "https://raw.githubusercontent.com/se-passau/vara-perf-tests/master/examples/min-1.c"})
class MinPerf1(prj.Project):
    """ minperf 1 """

    NAME = 'minperf1'
    GROUP = 'Perf'
    DOMAIN = 'Perf'

    SRC_FILE = "min-1.c"

    def run_tests(self, experiment):
        pass

    def compile(self):
        self.download()

        clang = cc(self)
        run(clang[self.SRC_FILE, "-o", "minperf1"])
