"""Project file for libssh."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make, cmake, mkdir
from benchbuild.utils.revision_ranges import (
    block_revisions,
    GoodBadSubgraph,
    RevisionRange,
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
    get_all_revisions_between,
    RevisionBinaryMap,
)
from varats.utils.settings import bb_cfg


class Libssh(VProject):
    """
    SSH library.

    (fetched by Git)
    """

    NAME = 'libssh'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.PROTOCOL

    SOURCE = [
        block_revisions([
            GoodBadSubgraph(["c65f56aefa50a2e2a78a0e45564526ecc921d74f"],
                            ["0151b6e17041c56813c882a3de6330c82acc8d93"],
                            "Disabled to quickly get this running")
        ])(
            PaperConfigSpecificGit(
                project_name="libssh",
                remote="https://github.com/libssh/libssh-mirror.git",
                local="libssh",
                refspec="origin/HEAD",
                limit=None,
                shallow=False
            )
        )
    ]

    CONTAINER = get_base_image(
        ImageBase.DEBIAN_10
    ).run('apt', 'install', '-y', 'libssl-dev', 'cmake')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Libssh.NAME))

        binary_map.specify_binary(
            'build/src/libssh.so',
            BinaryType.SHARED_LIBRARY,
            only_valid_in=RevisionRange("c65f56aefa", "9c4baa7fd5")
        )

        binary_map.specify_binary(
            'build/lib/libssh.so',
            BinaryType.SHARED_LIBRARY,
            only_valid_in=RevisionRange("d85bc347d3", "master")
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        libssh_source = local.path(self.source_of(self.primary_source))
        libssh_version = ShortCommitHash(self.version_of_primary)
        cmake_revisions = get_all_revisions_between(
            "0151b6e17041c56813c882a3de6330c82acc8d93", "master",
            ShortCommitHash, libssh_source
        )
        if libssh_version in cmake_revisions:
            self.__compile_cmake()
        else:
            self.__compile_make()

    def __compile_cmake(self) -> None:
        libssh_source = local.path(self.source_of(self.primary_source))

        compiler = bb.compiler.cc(self)
        mkdir("-p", libssh_source / "build")
        with local.cwd(libssh_source / "build"):
            with local.env(CC=str(compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(libssh_source):
            verify_binaries(self)

    def __compile_make(self) -> None:
        libssh_source = local.path(self.source_of(self.primary_source))
        libssh_version = ShortCommitHash(self.version_of_primary)
        autoconf_revisions = get_all_revisions_between(
            "5e02c25291d594e01a910fce097a3fc5084fd68f",
            "21e639cc3fd54eb3d59568744c9627beb26e07ed", ShortCommitHash,
            libssh_source
        )
        autogen_revisions = get_all_revisions_between(
            "ca32b0aa146b31d7772f27d16098845e615432aa",
            "ee54acb417c5589a8dc9dab0676f34b3d40a182b", ShortCommitHash,
            libssh_source
        )
        compiler = bb.compiler.cc(self)
        with local.cwd(libssh_source):
            with local.env(CC=str(compiler)):
                if libssh_version in autogen_revisions:
                    bb.watch("./autogen.sh")()
                if libssh_version in autoconf_revisions:
                    bb.watch("autoreconf")()
                configure = bb.watch(local["./configure"])
                configure()
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Libssh", "Libssh")]
