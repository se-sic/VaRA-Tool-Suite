"""Project file for openssl."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import git, make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper_mgmt.paper_config import PaperConfigSpecificGit
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


class OpenSSL(VProject):
    """TLS-framework OpenSSL (fetched by Git)"""

    NAME = 'openssl'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.SECURITY

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="openssl",
            remote="https://github.com/openssl/openssl.git",
            local="openssl",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10
                              ).run('apt', 'install', '-y', 'perl')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(OpenSSL.NAME))

        binary_map.specify_binary("libssl.so", BinaryType.SHARED_LIBRARY)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        openssl_git_path = get_local_project_git_path(self.NAME)
        openssl_version = ShortCommitHash(self.version_of_primary)
        openssl_source = local.path(self.source_of_primary)

        with local.cwd(openssl_git_path):
            configure_bug_revisions = get_all_revisions_between(
                "486f149131e94c970da1b89ebe8c66ab88e5d343",
                "5723a8ec514930c7c49d080cd7a2b17a8f8c7afa", ShortCommitHash
            )

        compiler = bb.compiler.cc(self)
        with local.cwd(openssl_source):
            if openssl_version in configure_bug_revisions:
                bb.watch(git)(
                    'cherry-pick', '-n',
                    '09803e9ce3a8a555e7014ebd11b4c80f9d300cf0'
                )
            with local.env(CC=str(compiler)):
                bb.watch(local['./config'])()
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("openssl_project", "openssl"), ("openssl", "openssl")]
