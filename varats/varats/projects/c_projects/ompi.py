"""Project file for the open-mpi."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make, mkdir
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


class Ompi(VProject):

    NAME = 'ompi'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.MPI

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="ompi",
            remote="https://github.com/open-mpi/ompi",
            local="ompi",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        bb.source.GitSubmodule(
            remote="https://github.com/openpmix/prrte.git",
            local="ompi/3rd-party/prrte",
            refspec="heads/master",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("ompi")
        ),
        bb.source.GitSubmodule(
            remote="https://github.com/openpmix/openpmix.git",
            local="ompi/3rd-party/openpmix",
            refspec="heads/master",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("ompi")
        ),
        bb.source.GitSubmodule(
            remote="https://github.com/open-mpi/oac",
            local="ompi/config/oac",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("ompi")
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Ompi.NAME))

        binary_map.specify_binary("ompi/ompi", BinaryType.EXECUTABLE)

        return binary_map[revision]


    def compile(self) -> None:
        ompi_source = local.path(self.source_of_primary)
        compiler = bb.compiler.cc(self)
        with local.cwd(ompi_source):
            with local.env(CC=str(compiler)):
                # bb.watch(local["./autogen.pl"])()
                # bb.watch(local["./configure"])("--disable-gcc-warnings")
                try:
                    bb.watch(local["./autogen.pl"])()
                    bb.watch(local["./configure"])("--disable-gcc-warnings")
                except Exception as e:
                    print(f"配置过程中出现错误: {e}")
                    # 输出config.log的内容以便调试
                    config_log_path = ompi_source / "config.log"
                    if config_log_path.is_file():
                        with open(config_log_path, "r") as log_file:
                            print(log_file.read())
                    return

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

