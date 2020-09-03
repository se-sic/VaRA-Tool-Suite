"""Project file for irssi."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.data.provider.cve.cve_provider import CVEProviderHook
from varats.paper.paper_config import project_filter_generator
from varats.utils.project_util import (
    wrap_paths_to_binaries,
    ProjectBinaryWrapper,
)
from varats.utils.settings import bb_cfg


class Irssi(bb.Project, CVEProviderHook):  # type: ignore
    """
    Irssi is a modular chat client that is most commonly known for its text mode
    user interface.

    (fetched by Git)
    """

    NAME = 'irssi'
    GROUP = 'c_projects'
    DOMAIN = 'chat'

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/irssi/irssi.git",
            local="irssi",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("irssi")
        )
    ]

    @property
    def binaries(self) -> tp.List[ProjectBinaryWrapper]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries(['./src/fe-text/irssi'])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        irssi_source = local.path(self.source_of(self.primary_source))

        compiler = bb.compiler.cc(self)
        with local.cwd(irssi_source):
            with local.env(CC=str(compiler)):
                bb.watch(local["./autogen.sh"])()
                bb.watch(local["./configure"])()

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Irssi", "Irssi")]
