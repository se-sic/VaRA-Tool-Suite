from benchbuild.utils.downloader import Wget
from benchbuild.utils.run import run
import benchbuild.project as prj

from plumbum import local

class fib(prj.Project):
    """ Fibonacci """

    NAME = 'fib'
    GROUP = 'Perf'
    DOMAIN = 'Perf'

    src_dir = "fib.c"
    git_uri = "https://raw.githubusercontent.com/se-passau/vara-perf-examples/master/examples/" + src_dir
    EnvVars = {}

    def run_tests(self, experiment, runner):
        pass

    def download(self):
        Wget(self.git_uri, self.src_dir)

    def build(self):
        with local.env(**self.EnvVars):
            clang = local["/home/hellmich/git/llvm/build/dev/bin/clang"]
            run(clang["-S", "-emit-llvm", "-fvara-handleRM=High", "normal-fib.c", "-o", "fib"])
