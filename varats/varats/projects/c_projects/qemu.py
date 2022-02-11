"""Project file for qemu."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

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


class Qemu(VProject):
    """
    QEMU, the FAST!

    processor emulator.
    """

    NAME = 'qemu'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.HW_EMULATOR

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="qemu",
            remote="https://github.com/qemu/qemu.git",
            local="qemu",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Qemu.NAME))

        binary_map.specify_binary(
            "build/x86_64-softmmu/qemu-system-x86_64", BinaryType.EXECUTABLE
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        qemu_source = local.path(self.source_of_primary)

        self.cflags += ['-Wno-tautological-type-limit-compare']

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)
        build_folder = qemu_source / "build"
        build_folder.mkdir()

        with local.cwd(build_folder):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                configure = bb.watch(local["../configure"])
                configure(
                    "--disable-debug-info", "--target-list=x86_64-softmmu"
                )
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("qemu", "qemu")]
