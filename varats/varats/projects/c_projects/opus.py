"""Project file for opus."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper_mgmt.paper_config import project_filter_generator
from varats.project.project_util import (
    wrap_paths_to_binaries,
    ProjectBinaryWrapper,
    BinaryType,
)
from varats.utils.settings import bb_cfg


class Opus(bb.Project):  # type: ignore
    """Opus is a codec for interactive speech and audio transmission over the
    Internet."""

    NAME = 'opus'
    GROUP = 'c_projects'
    DOMAIN = 'codec'

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/xiph/opus.git",
            local="opus",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("opus")
        )
    ]

    @property
    def binaries(self) -> tp.List[ProjectBinaryWrapper]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries([
            (".libs/opus_demo", BinaryType.executable)
        ])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        opus_source = local.path(self.source_of_primary)

        self.cflags += ["-fPIC"]

        clang = bb.compiler.cc(self)  # type: ignore
        with local.cwd(opus_source):
            with local.env(CC=str(clang)):
                bb.watch(local["./autogen.sh"])()  # type: ignore
                bb.watch(local["./configure"])()  # type: ignore
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))  # type: ignore

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("opus-codec", "opus")]
