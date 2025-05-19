"""Project file for MangoHUD (based on mpv's project file)."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import cmake, make, meson, ninja, pip
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


class MangoHud(VProject):
    """MangoHud is A Vulkan and OpenGL overlay for monitoring FPS, temperatures,
    CPU/GPU load and more."""

    NAME = 'mangohud'
    # C 55.2%
    # C++ 40.4%
    # Python 1.9%
    # Is this really a C project?
    GROUP = 'c_projects'
    # It's like a dashboard, isn't it?
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="mangohud",
            remote="https://github.com/flightlessmango/MangoHud.git",
            local="mangohud",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_12).run(
        'apt', 'install', '-y', 'debhelper-compat', 'meson', 'pkg-config',
        'glslang-tools', 'mesa-common-dev', 'libdbus-1-dev', 'libdrm-dev',
        'libvulkan-dev', 'libglew-dev', 'libopengl-dev', 'nlohmann-json3-dev',
        'libglfw3-dev', 'libspdlog-dev', 'libx11-dev', 'libwayland-dev',
        'libxnvctrl-dev', 'libxrandr-dev', 'python3-mako', 'python3-setuptools',
        'gcc', 'g++', 'gcc-multilib', 'g++-multilib', 'ninja-build',
        'python3-pip', 'python3-setuptools', 'python3-wheel', 'pkg-config',
        'mesa-common-dev', 'libx11-dev', 'libxnvctrl-dev', 'libdbus-1-dev',
        'libxkbcommon-x11-dev'
    )
    # The packages following gcc (inclusive) were copied from the Debian
    # installation script. libxkbcommon-x11-dev was included because compilation
    # would fail without it.

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(MangoHud.NAME)
        )

        # There’s also ./build/src/libMangoHud_opengl.so
        binary_map.specify_binary(
            "build/src/libMangoHud.so", BinaryType.SHARED_LIBRARY
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        mangohud_version_source = local.path(self.source_of_primary)

        compiler = bb.compiler.cc(self)
        with local.cwd(mangohud_version_source):

            with local.env(CC=str(compiler)):
                bb.watch(pip)('install', 'mako')
                bb.watch(meson)('setup', 'build')
                bb.watch(ninja)('-C', 'build')

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("flightlessmango", "mangohud")]
