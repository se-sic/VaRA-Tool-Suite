from benchbuild.utils.downloader import Wget
from benchbuild.utils.run import run
from benchbuild.utils.compiler import cc
import benchbuild.project as prj

from plumbum import local

class Gcd(prj.Project):
    """ GCD """

    NAME = 'gcd'
    GROUP = 'Perf'
    DOMAIN = 'Perf'

    src_dir = "gcd.c"
    git_uri = "https://raw.githubusercontent.com/se-passau/vara-perf-tests/master/examples/" + src_dir

    def run_tests(self, experiment):
        pass

    def download(self):
        Wget(self.git_uri, self.src_dir)

    def build(self):
        clang = cc(self)
        run(clang[self.src_dir, "-o", "gcd"])
