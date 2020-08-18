"""Project file for gawk."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper.paper_config import project_filter_generator
from varats.settings import bb_cfg
from varats.utils.project_util import (
    wrap_paths_to_binaries,
    ProjectBinaryWrapper,
)


class Gawk(bb.Project):  # type: ignore
    """
    GNU awk.

    (fetched by Git)
    """

    NAME = 'gawk'
    GROUP = 'c_projects'
    DOMAIN = 'interpreter'

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/Distrotech/gawk.git",
            local="gawk",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("gawk")
        )
    ]

    @property
    def binaries(self) -> tp.List[ProjectBinaryWrapper]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries(['gawk'])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        gawk_source = bb.path(self.source_of(self.primary_source))

        compiler = bb.compiler.cc(self)
        with local.cwd(gawk_source):
            with local.env(CC=str(compiler)):
                bb.watch(local["./configure"])()

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
