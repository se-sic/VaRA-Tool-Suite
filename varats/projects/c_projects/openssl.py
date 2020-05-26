"""Project file for openssl."""
import typing as tp

from benchbuild.project import Project
from benchbuild.utils.cmd import make
from benchbuild.utils.compiler import cc
from benchbuild.utils.download import with_git
from benchbuild.utils.run import run
from plumbum import local

from varats.data.provider.cve.cve_provider import CVEProviderHook
from varats.paper.paper_config import project_filter_generator
from varats.settings import get_benchbuild_config
from varats.utils.project_util import (
    wrap_paths_to_binaries,
    ProjectBinaryWrapper,
)


@with_git(
    "https://github.com/openssl/openssl.git",
    refspec="HEAD",
    version_filter=project_filter_generator("openssl")
)
class OpenSSL(Project, CVEProviderHook):  # type: ignore
    """TLS-framework OpenSSL (fetched by Git)"""

    NAME = 'openssl'
    GROUP = 'c_projects'
    DOMAIN = 'security'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)

    @property
    def binaries(self) -> tp.List[ProjectBinaryWrapper]:
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
            run(make["-j", int(get_benchbuild_config()["jobs"])])

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("openssl_project", "openssl"), ("openssl", "openssl")]
