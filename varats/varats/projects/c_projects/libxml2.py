"""Project file for libxml2."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make, cmake
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


class Libxml2(VProject):
    """libxml2 is a software library for parsing XML documents."""

    NAME = 'libxml2'
    GROUP = 'c_projects'
    DOMAIN = 'XML document library'

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/GNOME/libxml2.git",
            local="libxml2",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("libxml2")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10)\
        .run('apt', 'install', '-y', 'wget', 'liblzma-dev')\
        .run('/bin/bash', '-c',
             'wget -qO- '
             '\"https://cmake.org/files/v3.20'
             '/cmake-3.20.0-linux-x86_64.tar.gz\" '
             '| tar --strip-components=1 -xz -C /usr/local')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([
            ("libxml2.so", BinaryType.SHARED_LIBRARY)
        ])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        libxml2_version_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        with local.cwd(libxml2_version_source):
            with local.env(CC=str(c_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", ".")
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Xmlsoft", "Libxml2")]
