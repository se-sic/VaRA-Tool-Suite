"""Project file for the bcc."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make, mkdir, cmake, sudo
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper.paper_config import (
    project_filter_generator,
    PaperConfigSpecificGit,
)
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


class Bcc(VProject):

    NAME = 'bcc'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="bcc",
            remote="https://github.com/iovisor/bcc",
            local="bcc",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        bb.source.GitSubmodule(
            remote="https://github.com/libbpf/libbpf.git",
            local="bcc/src/cc/libbpf",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("bcc")
        ),
        bb.source.GitSubmodule(
            remote="https://github.com/libbpf/bpftool",
            local="bcc/libbpf-tools/bpftool",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("bcc")
        ),
        bb.source.GitSubmodule(
            remote="https://github.com/libbpf/blazesym",
            local="bcc/ibbpf-tools/blazesym",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("bcc")
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Bcc.NAME))

        binary_map.specify_binary("build/src/cc/libbcc.so.0.30.0", BinaryType.SHARED_LIBRARY)

        return binary_map[revision]

    def compile(self) -> None:
        """Compile the BCC project."""
        bcc_source = local.path(self.source_of_primary)
        mkdir("-p", bcc_source / "build")

        cc_compiler = bb.compiler.cc(self)
        with local.cwd(bcc_source / 'build'):
            with local.env(CC=str(cc_compiler)):
                llvm_path = "/lib/llvm-14/lib/cmake/llvm/"
                bb.watch(cmake)("..", "-DCMAKE_BUILD_TYPE=Release", f"-DLLVM_DIR={llvm_path}",
                                "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
                                "-DCMAKE_C_FLAGS=-fPIE", "-DCMAKE_CXX_FLAGS=-fPIE",
                                "-DCMAKE_EXE_LINKER_FLAGS=-pie"
                                )  # Configuring the project

            # Compiling the project with make, specifying the number of jobs
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

