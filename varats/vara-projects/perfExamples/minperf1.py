from benchbuild.utils.cmd import cp
from benchbuild.utils.run import run
import benchbuild.project as prj

from plumbum import local

class minperf1(prj.Project):
    """ minperf 1 """

    NAME = 'minperf1'

    src_dir = NAME
    file_path = "/home/hellmich/git/vara-perf-examples/examples/min-1.c"
    EnvVars = {}

    def configure(self):
        with local.cwd(self.src_dir):
            cp(file_path, ".")

    def build(self):
        with local.cwd(self.src_dir):
            with local.env(**self.EnvVars):
                clang = local["clang"]
                run(clang["min-1.c"])
