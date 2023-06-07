"""Project file for curl."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.revision_ranges import block_revisions, GoodBadSubgraph
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper.paper_config import PaperConfigSpecificGit
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


class Curl(VProject):
    """
    Curl is a command-line tool for transferring data specified with URL syntax.

    (fetched by Git)
    """

    NAME = 'curl'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.WEB_TOOLS

    SOURCE = [
        block_revisions([
            GoodBadSubgraph(["3af90a6e19249807f99bc9ee7b50d3e58849072a"],
                            ["30ef1a077996c71e463beae53354e8ffc7a4c90d"],
                            "Compile error without ssl"),
            GoodBadSubgraph(["ae1912cb0d494b48d514d937826c9fe83ec96c4d"],
                            ["98dcde4ec3397d8626e2c8f29abaf481fc42e8ec"],
                            "Requires old libtool version")
        ])(
            PaperConfigSpecificGit(
                project_name="curl",
                remote="https://github.com/curl/curl.git",
                local="curl",
                refspec="origin/HEAD",
                limit=None,
                shallow=False
            )
        )
    ]

    CONTAINER = get_base_image(
        ImageBase.DEBIAN_10
    ).run('apt', 'install', '-y', 'autoconf', 'automake', 'libtool', 'openssl')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Curl.NAME))

        binary_map.specify_binary('src/.libs/curl', BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        curl_source = local.path(self.source_of_primary)

        clang = bb.compiler.cc(self)
        with local.cwd(curl_source):
            with local.env(CC=str(clang)):
                bb.watch(local["./buildconf"])()
                bb.watch(local["./configure"])("--without-ssl")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Haxx", "Curl")]
