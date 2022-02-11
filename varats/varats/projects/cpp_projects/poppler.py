"""Project file for poppler."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import cmake, make
from benchbuild.utils.revision_ranges import block_revisions, RevisionRange
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper_mgmt.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    get_local_project_git_path,
    BinaryType,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap
from varats.utils.settings import bb_cfg


class Poppler(VProject):
    """Poppler is a free software utility library for rendering Portable
    Document Format documents."""

    NAME = 'poppler'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.RENDERING

    SOURCE = [
        block_revisions([
            RevisionRange(
                "e225b4b804881de02a5d1beb3f3f908a8f8ddc3d",
                "2b2808719d2c91283ae358381391bb0b37d9061d",
                "requiers QT6 which is not easily available"
            )
        ])(
            PaperConfigSpecificGit(
                project_name="poppler",
                remote="https://gitlab.freedesktop.org/poppler/poppler.git",
                local="poppler",
                refspec="origin/HEAD",
                limit=None,
                shallow=False
            )
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', 'cmake', 'libfreetype6-dev',
        'libfontconfig-dev', 'libjpeg-dev', 'qt5-default', 'libopenjp2-7-dev'
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Poppler.NAME))

        binary_map.specify_binary("libpoppler.so", BinaryType.SHARED_LIBRARY)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        poppler_version_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)
        with local.cwd(poppler_version_source):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", ".")
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Poppler", "Poppler")]
