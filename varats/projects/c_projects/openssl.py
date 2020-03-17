"""
Project file for openssl.
"""
import typing as tp
from pathlib import Path

from benchbuild.project import Project
from benchbuild.settings import CFG as BB_CFG
from benchbuild.utils.cmd import make
from benchbuild.utils.compiler import cc
from benchbuild.utils.download import with_git
from benchbuild.utils.run import run

from plumbum import local

from varats.paper.paper_config import project_filter_generator
from varats.utils.project_util import wrap_paths_to_binaries


@with_git("https://github.com/openssl/openssl.git",
          refspec="HEAD",
          version_filter=project_filter_generator("openssl"))
class OpenSSL(Project):  # type: ignore
    """ TLS-framework OpenSSL (fetched by Git) """

    NAME = 'openssl'
    GROUP = 'c_projects'
    DOMAIN = 'security'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)

    @property
    def binaries(self) -> tp.List[Path]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries(["libssl.so"])

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        compiler = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(compiler)):
                run(local['./config'])
            run(make["-j", int(BB_CFG["jobs"])])
