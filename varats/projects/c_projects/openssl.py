"""
Project file for openssl.
"""
from benchbuild.project import Project
from benchbuild.settings import CFG
from benchbuild.utils.cmd import make, autoreconf, cp
from benchbuild.utils.compiler import cc
from benchbuild.utils.download import with_git
from benchbuild.utils.run import run

from plumbum import local

from varats.paper.paper_config import project_filter_generator


@with_git(
    "https://github.com/openssl/openssl.git",
    refspec="HEAD",
    version_filter=project_filter_generator("openssl"))
class OpenSSL(Project):  # type: ignore
    """ TLS-framework OpenSSL (fetched by Git) """

    NAME = 'openssl'
    GROUP = 'c_projects'
    DOMAIN = 'security'
    VERSION = 'HEAD'

    BIN_NAMES = ['libssl.so']
    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                run(local['./config'])
            run(make["-j", int(CFG["jobs"])])
