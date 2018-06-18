from benchbuild.utils.downloader import Wget
from benchbuild.utils.run import run
from benchbuild.utils.compiler import lt_clang
import benchbuild.project as prj

from plumbum import local

class minperf3(prj.Project):
    """ minperf 3 """

    NAME = 'minperf3'
    GROUP = 'Perf'
    DOMAIN = 'Perf'

    src_dir = "min-3.c"
    git_uri = "https://raw.githubusercontent.com/se-passau/vara-perf-examples/master/examples/" + src_dir
    EnvVars = {}

    def run_tests(self, experiment, runner):
        pass

    def download(self):
        Wget(self.git_uri, self.src_dir)

    def build(self):
        clang = lt_clang(self.cflags, self.ldflags, self.compiler_extension)
        with local.env(**self.EnvVars):
            run(clang[self.src_dir, "-o", "minperf3"])
