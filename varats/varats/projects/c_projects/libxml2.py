"""Project file for libxml2."""
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.utils.cmd import make, cmake
from benchbuild.utils.revision_ranges import GoodBadSubgraph
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper.paper_config import PaperConfigSpecificGit
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


class Libxml2(VProject):
    """libxml2 is a software library for parsing XML documents."""

    NAME = 'libxml2'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.FILE_FORMAT

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="libxml2",
            remote="https://github.com/GNOME/libxml2.git",
            local="libxml2",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10) \
        .run('apt', 'install', '-y', 'wget', 'liblzma-dev') \
        .run('/bin/bash', '-c',
             'wget -qO- '
             '\"https://cmake.org/files/v3.20'
             '/cmake-3.20.0-linux-x86_64.tar.gz\" '
             '| tar --strip-components=1 -xz -C /usr/local')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Libxml2.NAME))

        binary_map.specify_binary("libxml2.so", BinaryType.SHARED_LIBRARY)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        libxml2_version_source = Path(self.source_of_primary)
        libxml2_versions_wo_cmake = GoodBadSubgraph([
            "01791d57d650e546a915522e57c079157a5bb395"
        ], ["2a2c38f3a35f415e7f407e171c07bb48bda0711e"], "No CmakeList")
        libxml2_version = self.version_of_primary
        c_compiler = bb.compiler.cc(self)
        with local.cwd(libxml2_version_source):
            with local.env(CC=str(c_compiler)):
                if libxml2_version in libxml2_versions_wo_cmake:
                    bb.watch(local["./configure"])
                else:
                    bb.watch(cmake)("-G", "Unix Makefiles", ".")
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Xmlsoft", "Libxml2")]
