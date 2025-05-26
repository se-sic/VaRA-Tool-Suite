"""Project file for libmgba0.10 (based on the brotli project file)."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import cmake, mkdir, make, find, echo
from benchbuild.utils.revision_ranges import (
    RevisionRange,
    block_revisions,
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


class Mgba(VProject):
    """mGBA emulator."""

    NAME = 'mgba'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="mgba",
            remote="https://github.com/mgba-emu/mgba",
            local="mgba",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    # taken from the Debian package
    # https://packages.debian.org/en/bookworm/libmgba0.10
    CONTAINER = get_base_image(ImageBase.DEBIAN_12).run(
        'apt', 'install', '-y', 'cmake', 'debhelper-compat',
        'desktop-file-utils', 'libavcodec-dev', 'libavfilter-dev',
        'libavformat-dev', 'libavutil-dev', 'libedit-dev', 'libelf-dev',
        'libinih-dev', 'liblua5.4-dev', 'libmagickwand-dev', 'libpng-dev',
        'libqt5opengl5-dev', 'libsdl2-dev', 'libsqlite3-dev',
        'libswresample-dev', 'libswscale-dev', 'libzip-dev', 'pkg-config',
        'qtbase5-dev', 'qtmultimedia5-dev', 'qttools5-dev-tools',
        'rapidjson-dev', 'zipcmp', 'zipmerge', 'ziptool', 'zlib1g-dev'
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Mgba.NAME))

        binary_map.specify_binary(
            "build/libmgba.so.0.11.0", BinaryType.SHARED_LIBRARY
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        mgba_version_source = local.path(self.source_of_primary)

        compiler = bb.compiler.cc(self)
        bb.watch(mkdir)(mgba_version_source / 'build')
        with local.cwd(mgba_version_source / 'build'):
            with local.env(CC=str(compiler)):

                bb.watch(cmake)('-DCMAKE_BUILD_TYPE=Debug', '..')
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(mgba_version_source):
            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("mgba-emu", "mgba")]
