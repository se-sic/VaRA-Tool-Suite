"""Project file for libssh."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make, cmake, mkdir
from benchbuild.utils.revision_ranges import block_revisions, GoodBadSubgraph
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper_mgmt.paper_config import project_filter_generator
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    wrap_paths_to_binaries,
    get_local_project_git_path,
    BinaryType,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, get_all_revisions_between
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
            bb.source.Git(
                remote="https://github.com/libssh/libssh-mirror.git",
                local="libssh",
                refspec="origin/HEAD",
                limit=None,
                shallow=False,
                version_filter=project_filter_generator("libssh")
            )
        )
    ]

    CONTAINER = get_base_image(
        ImageBase.DEBIAN_10
    ).run('apt', 'install', '-y', 'libssl-dev', 'cmake')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        libssh_git_path = get_local_project_git_path(Libssh.NAME)
        with local.cwd(libssh_git_path):
            versions_with_src_library_folder = get_all_revisions_between(
                "c65f56aefa50a2e2a78a0e45564526ecc921d74f",
                "9c4baa7fd58b9e4d9cdab4a03d18dd03e0e587ab", ShortCommitHash
            )
            if revision in versions_with_src_library_folder:
                return wrap_paths_to_binaries([
                    ('build/src/libssh.so', BinaryType.SHARED_LIBRARY)
                ])

            return wrap_paths_to_binaries([
                ('build/lib/libssh.so', BinaryType.SHARED_LIBRARY)
            ])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        libssh_source = local.path(self.source_of(self.primary_source))
        compiler = bb.compiler.cc(self)
        mkdir("-p", libssh_source / "build")
        with local.cwd(libssh_source / "build"):
            with local.env(CC=str(compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(libssh_source):
            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Libssh", "Libssh")]
