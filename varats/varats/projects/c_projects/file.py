"""Project file for file."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make, autoreconf
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
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class File(VProject):
    """File command for recognizing the type of data contained in a file."""

    NAME = 'file'
    GROUP = 'c_projects'
    DOMAIN = 'command'

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/file/file",
            local="file_git",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("file")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', 'autoconf', 'automake', 'autotools-dev',
        'build-essential'
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([
            ("src/.libs/file", BinaryType.EXECUTABLE)
        ])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        file_version_source = local.path(self.source_of_primary)

        self.cflags += ["-fPIC"]

        c_compiler = bb.compiler.cc(self)
        with local.cwd(file_version_source):
            with local.env(CC=str(c_compiler)):
                bb.watch(autoreconf["-f", "-i"])()
                bb.watch(local["./configure"])()
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(file_version_source):
            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("File Project", "file")]
