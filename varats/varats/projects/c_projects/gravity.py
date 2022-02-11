"""Project file for gravity."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import cmake, make
from benchbuild.utils.revision_ranges import (
    block_revisions,
    GoodBadSubgraph,
    RevisionRange,
    SingleRevision,
)
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper_mgmt.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    get_local_project_git_path,
    BinaryType,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import (
    ShortCommitHash,
    RevisionBinaryMap,
    get_all_revisions_between,
)
from varats.utils.settings import bb_cfg


class Gravity(VProject):
    """Programming language Gravity."""

    NAME = 'gravity'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.PROG_LANG

    SOURCE = [
        block_revisions([
            RevisionRange(
                "0b8e0e047fc3d5e18ead3221ad54920f1ad0eedc",
                "8f417752dd14deea64249b5d32b6138ebc877fa9", "nothing to build"
            ),
            GoodBadSubgraph(["e8999a84efbd9c3e739bff7af39500d14e61bfbc"],
                            ["0e918ce0798407dd6c981e1cd26b4ba138d22fab"],
                            "missing -lm"),
            GoodBadSubgraph(["244c5aa91358a5b2472d351e6c7f38ba7da94ef6"],
                            ["371152de2f38534d4da332349d1def83fc66d5bc"],
                            "Visual studio project breaks makefile"),
            GoodBadSubgraph(["112be515b5ef3b67011c7272e5a50ac3a1fcadc4"],
                            ["b9a62dfad41ae06d029493cf4d5757de2a0281b2"],
                            "bug in gravity"),
            SingleRevision(
                "e207f0cc87bf57e9ccb6f0d18ff4fe4d6ef0c096", "bug in gravity"
            ),
            GoodBadSubgraph(["d2a04f92347fb5f2b6fd23bea9b0e12817cd6d8e"],
                            ["e8fbd6a4a2a9618456f1460dc9138b617dc7af4b"],
                            "bug in gravity"),
            GoodBadSubgraph(["968534c5d4f28501b7f34da48cab2c153ae7449b"],
                            ["0caf15328bda90ffb1911077e03b28ea9970208b"],
                            "bug in gravity"),
            GoodBadSubgraph(["e4f95e669a4c5cf2d142d5b0b72a11c117f7092f"],
                            ["09e59da4deff9b35224f4784fae9d0f132be9cea"],
                            "missing -lbsd"),
        ])(
            PaperConfigSpecificGit(
                project_name="gravity",
                remote="https://github.com/marcobambini/gravity.git",
                local="gravity",
                refspec="origin/HEAD",
                limit=None,
                shallow=False
            )
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10
                              ).run('apt', 'install', '-y', 'cmake')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Gravity.NAME))

        binary_map.specify_binary("gravity", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        gravity_git_path = get_local_project_git_path(self.NAME)
        gravity_version = self.version_of_primary

        # commit 46133fb47d6da1f0dec27ae23db1d633bc72e9e3 introduced
        # cmake as build system
        with local.cwd(gravity_git_path):
            cmake_revisions = get_all_revisions_between(
                "dbb4d61fc2ebb9aca44e8e6bb978efac4a6def87", "master",
                ShortCommitHash
            )

        if gravity_version in cmake_revisions:
            self.__compile_cmake()
        else:
            self.__compile_make()

    def __compile_cmake(self) -> None:
        gravity_version_source = local.path(self.source_of_primary)
        clang = bb.compiler.cc(self)
        with local.cwd(gravity_version_source):
            with local.env(CC=str(clang)):
                bb.watch(cmake)("-G", "Unix Makefiles", ".")
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    def __compile_make(self) -> None:
        gravity_version_source = local.path(self.source_of_primary)
        clang = bb.compiler.cc(self)
        with local.cwd(gravity_version_source):
            with local.env(CC=str(clang)):
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("creolabs", "gravity")]
