"""Project file for htop."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper_mgmt.paper_config import project_filter_generator
from varats.project.project_util import (
    ProjectBinaryWrapper,
    wrap_paths_to_binaries,
    BinaryType,
    verify_binaries,
)
from varats.utils.settings import bb_cfg


class Htop(bb.Project):  # type: ignore
    """Process visualization tool (fetched by Git)"""

    NAME = 'htop'
    GROUP = 'c_projects'
    DOMAIN = 'visualization'

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/hishamhm/htop.git",
            local="htop",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("htop")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', 'autoconf', 'automake', 'autotools-dev',
        'libtool'
    )

    @property
    def binaries(self) -> tp.List[ProjectBinaryWrapper]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries([('htop', BinaryType.EXECUTABLE)])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        htop_source = local.path(self.source_of_primary)

        clang = bb.compiler.cc(self)
        with local.cwd(htop_source):
            with local.env(CC=str(clang)):
                bb.watch(local["./autogen.sh"])()
                bb.watch(local["./configure"])()

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Htop", "Htop")]
