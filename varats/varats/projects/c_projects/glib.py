"""Project file for glib."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import ninja, meson
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper_mgmt.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    verify_binaries,
    get_local_project_git_path,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap
from varats.utils.settings import bb_cfg


class Glib(VProject):
    """
    GLib is the low-level core library that forms the basis for projects such as
    GTK and GNOME. It provides data structure handling for C, portability
    wrappers, and interfaces for such runtime functionality as an event loop,
    threads, dynamic loading, and an object system.

    (fetched by Git)
    """

    NAME = 'glib'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.DATA_STRUCTURES

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="glib",
            remote="https://github.com/GNOME/glib.git",
            local="glib",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(
        ImageBase.DEBIAN_10
    ).run('apt', 'install', '-y', 'meson', 'ninja-build')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Glib.NAME))

        binary_map.specify_binary(
            'build/glib/libglib-2.0.so', BinaryType.SHARED_LIBRARY
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        glib_source = local.path(self.source_of_primary)

        cc_compiler = bb.compiler.cc(self)
        with local.cwd(glib_source):
            with local.env(CC=str(cc_compiler)):
                bb.watch(meson)("build")

            bb.watch(ninja)("-j", get_number_of_jobs(bb_cfg()), "-C", "build")

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Gnome", "Glib")]
