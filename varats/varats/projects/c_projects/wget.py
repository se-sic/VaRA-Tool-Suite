"""Project file for curl."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.revision_ranges import block_revisions, GoodBadSubgraph
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper.paper_config import (
    PaperConfigSpecificGit,
    project_filter_generator,
)
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    verify_binaries,
    get_local_project_repo,
    RevisionBinaryMap,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class WGet(VProject):
    """
    Curl is a command-line tool for transferring data specified with URL syntax.

    (fetched by Git)
    """

    NAME = 'wget'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.WEB_TOOLS

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="wget",
            remote="https://github.com/mirror/wget.git",
            local="wget",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        bb.source.GitSubmodule(
            remote="https://github.com/coreutils/gnulib.git",
            local="wget/gnulib",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("wget")
        ),
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', 'autoconf', 'automake', 'libtool',
        'autoconf-archive', 'libgnutls28-dev'
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(WGet.NAME))

        binary_map.specify_binary('src/wget', BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        wget_source = local.path(self.source_of_primary)
        self.cflags += [
            "-Wno-error=string-plus-int",
            "-Wno-error=shift-negative-value",
            "-Wno-string-plus-int",
            "-Wno-shift-negative-value",
        ]
        clang = bb.compiler.cc(self)
        with local.cwd(wget_source):
            with local.env(CC=str(clang)):
                bb.watch(local["./bootstrap"])()
                bb.watch(local["./configure"])()

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("wget", "wget"), ("gnu", "wget")]
