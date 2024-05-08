"""Project file for the Crun."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
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


class Crun(VProject):

    NAME = 'crun'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.RUNTIME

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="crun",
            remote="https://github.com/containers/crun",
            local="crun",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        bb.source.GitSubmodule(
            remote="https://github.com/containers/libocispec.git",
            local="crun/libocispec",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("crun")
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Crun.NAME))

        binary_map.specify_binary("crun", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def compile(self) -> None:
        crun_source = local.path(self.source_of_primary)
        compiler = bb.compiler.cc(self)
        with local.cwd(crun_source):
            with local.env(CC=str(compiler)):
                bb.watch(local["./autogen.sh"])()
                bb.watch(local["./configure"])("--disable-gcc-warnings")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

