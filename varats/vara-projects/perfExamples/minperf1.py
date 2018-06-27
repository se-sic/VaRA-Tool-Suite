from benchbuild.utils.downloader import Wget
from benchbuild.utils.run import run
from benchbuild.utils.compiler import cc
import benchbuild.project as prj

from plumbum import local

class minperf1(prj.Project):
    """ minperf 1 """

    NAME = 'minperf1'
    GROUP = 'Perf'
    DOMAIN = 'Perf'

    src_dir = "min-1.c"
    git_uri = "https://raw.githubusercontent.com/se-passau/vara-perf-examples/master/examples/" + src_dir
    EnvVars = {}

    def run_tests(self, experiment, runner):
        pass

    def download(self):
        Wget(self.git_uri, self.src_dir)

    def build(self):
        clang = cc(self)
        with local.env(**self.EnvVars):
            run(clang[self.src_dir, "-o", "minperf1"])
