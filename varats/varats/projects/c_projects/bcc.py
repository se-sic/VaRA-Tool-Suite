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

        binary_map.specify_binary("build/bcc", BinaryType.EXECUTABLE)

        return binary_map[revision]

    # def compile(self) -> None:
    #     bcc_source = local.path(self.source_of_primary)
    #     compiler = bb.compiler.cc(self)
    #     with local.cwd(bcc_source):
    #         with local.env(CC=str(compiler)):
    #             # 使用 CMake 来配置项目
    #             bb.watch(local["mkdir"])("-p", "build")  # 创建构建目录
    #             with local.cwd("build"):
    #                 bb.watch(local["cmake"])("..", "-DCMAKE_BUILD_TYPE=Release")
    #                 # 根据需要添加其他CMake配置选项，如指定编译器或禁用特定特性
    #
    #         # 在构建目录下执行 make
    #         with local.cwd("build"):
    #             bb.watch(cmake)("-j", get_number_of_jobs(bb_cfg()))
    #
    #         # 校验编译后的二进制文件
    #         verify_binaries(self)

    def compile(self) -> None:
        bcc_source = local.path(self.source_of_primary)
        compiler = bb.compiler.cc(self)
        with local.cwd(bcc_source):
            with local.env(CC=str(compiler)):
                # 创建构建目录
                mkdir("-p", "build")
                with local.cwd("build"):
                    # 设置 LLVM 的路径
                    llvm_path = "/lib/llvm-14/lib/cmake/llvm/"
                    # 使用 CMake 配置项目，并指定 LLVM 的路径
                    bb.watch(local["cmake"])("..", "-DCMAKE_BUILD_TYPE=Release", f"-DLLVM_DIR={llvm_path}")
                    # 执行编译
                    bb.watch(local["make"])("-j", get_number_of_jobs(bb_cfg()))
                    # 执行安装（需要管理员权限）
                    bb.watch(local["sudo"][local["make"]["install"]])()

                    # 配置 Python 绑定
                    bb.watch(local["cmake"])("..", "-DPYTHON_CMD=python3")

                    # 构建并安装 Python 绑定
                with local.cwd("src/python"):
                    bb.watch(local["make"])()
                    bb.watch(local["sudo"][local["make"]["install"]])()

                # 校验编译后的二进制文件
            verify_binaries(self)
