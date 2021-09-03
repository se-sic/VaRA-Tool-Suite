"""Project file for gawk."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper_mgmt.paper_config import project_filter_generator
from varats.project.project_util import (
    wrap_paths_to_binaries,
    ProjectBinaryWrapper,
    BinaryType,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class Gawk(VProject):
    """
    GNU awk.

    (fetched by Git)
    """

    NAME = 'gawk'
    GROUP = 'c_projects'
    DOMAIN = 'interpreter'

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/vulder/gawk.git",
            local="gawk",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("gawk")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', 'autoconf', 'automake', 'libtool', 'perl', 'm4',
        'autopoint', 'gettext', 'bison'
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([('gawk', BinaryType.EXECUTABLE)])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        gawk_source = local.path(self.source_of(self.primary_source))

        compiler = bb.compiler.cc(self)
        with local.cwd(gawk_source):
            with local.env(CC=str(compiler)):
                bb.watch(local["autoreconf"])("-if")
                bb.watch(local["./configure"])()

            bb.watch(make)("MAKEINFO=true", "-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)
