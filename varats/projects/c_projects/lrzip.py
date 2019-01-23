from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.run import run
import benchbuild.project as prj
from benchbuild.utils.cmd import make
from benchbuild.utils.download import with_git, Git, Copy

from plumbum import local


@with_git("https://github.com/ckolivas/lrzip.git", limit=100, refspec="HEAD")
class Lrzip(prj.Project):
    NAME = 'lrzip'
    GROUP = 'encoder'
    DOMAIN = 'version control'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner):
        pass

    def compile(self):
        self.download()
        self.download_em_config()
        
        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                run(local["./autogen.sh"])
            run(make["-j", int(CFG["jobs"])])

    def download_em_config(self):
        with local.cwd(self.SRC_FILE):
            Git("https://github.com/se-passau/EnergyMetering_CaseStudies.git",
                "em_config")
            Copy("em_config/lrzip/*", "..")
