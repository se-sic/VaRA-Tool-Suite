"""Project file for file."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make, autoreconf
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper_mgmt.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_git_path,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap
from varats.utils.settings import bb_cfg


class File(VProject):
    """File command for recognizing the type of data contained in a file."""

    NAME = 'file'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="file",
            remote="https://github.com/file/file",
            local="file_git",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', 'autoconf', 'automake', 'autotools-dev',
        'build-essential'
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(File.NAME))

        binary_map.specify_binary("src/.libs/file", BinaryType.EXECUTABLE)

        return binary_map[revision]

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
