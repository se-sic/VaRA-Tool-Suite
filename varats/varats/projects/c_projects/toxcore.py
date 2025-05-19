"""Project file for toxcore (partly based on gravity's project file IIRC)."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import cmake, make, mkdir
from benchbuild.utils.revision_ranges import (
    block_revisions,
    GoodBadSubgraph,
    RevisionRange,
    SingleRevision,
)
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
from varats.utils.git_util import (
    ShortCommitHash,
    RevisionBinaryMap,
    get_all_revisions_between,
)
from varats.utils.settings import bb_cfg


class Toxcore(VProject):
    """Tox is a peer to peer (serverless) instant messenger aimed at making
    security and privacy easy to obtain for regular users."""

    NAME = 'toxcore'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.C_LIBRARY

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="toxcore",
            remote="https://github.com/TokTok/c-toxcore.git",
            local="toxcore",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    # https://github.com/TokTok/c-toxcore/raw/refs/heads/master/INSTALL.md
    # libsodium, libm, libpthread, librt
    # are required to build toxcore.

    # Be advised that due to the addition of cmp as a submodule, you now also
    # need to initialize the git submodules required by toxcore.

    # Assuming all the requirements are met, just run
    # cmake -B _build

    CONTAINER = get_base_image(
        ImageBase.DEBIAN_12
    ).run('apt', 'install', '-y', 'libsodium-dev', 'pkg-config')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Toxcore.NAME))

        binary_map.specify_binary("libtoxcore.so", BinaryType.SHARED_LIBRARY)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        toxcore_version_source = local.path(self.source_of_primary)

        self.cflags += ['-fPIE']
        compiler = bb.compiler.cc(self)
        mkdir(toxcore_version_source / '_build')

        with local.cwd(
            toxcore_version_source / '_build'
        ):  # divison operator overloaded
            with local.env(CC=str(compiler)):
                # The following changes compile toxcore _without_ the AV library.

                # Toxcore will silently continue compiling even if toxav cannot
                # be found. That’s why I commented the following lines out.

                # > micro CMakeList.txt
                # > # change BUILD_TOXAV to OFF
                # > # option(BUILD_TOXAV "Whether to build the tox AV library" OFF)
                # bb.watch(local["sed"])(["-i", 's/option\(BUILD_TOXAV "Whether to build the tox AV library" ON\)/option\(BUILD_TOXAV "Whether to build the tox AV library" OFF\)/g', 'CMakeList.txt'])

                bb.watch(local['cmake'])('-DBUILD_TOXAV=OFF', '..')
                # > micro _build/CMakeFiles/Makefile2
                # > # comment the following lines out
                # > # all: CMakeFiles/unit_ring_buffer_test.dir/all
                # > # all: CMakeFiles/unit_rtp_test.dir/all
                bb.watch(local["sed"])([
                    "-i",
                    's/^all: CMakeFiles\/unit_ring_buffer_test.dir\/all/# all: CMakeFiles\/unit_ring_buffer_test.dir\/all/g',
                    'CMakeFiles/Makefile2'
                ])
                bb.watch(local["sed"])([
                    "-i",
                    's/^all: CMakeFiles\/unit_rtp_test.dir\/all/# all: CMakeFiles\/unit_rtp_test.dir\/all/g',
                    'CMakeFiles/Makefile2'
                ])

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        # The project’s actual name is ‘c-toxcore’.
        return [("TokTok", "toxcore")]
