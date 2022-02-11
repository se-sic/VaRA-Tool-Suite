"""Project file for libtiff."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.revision_ranges import (
    block_revisions,
    GoodBadSubgraph,
    SingleRevision,
)
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
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap
from varats.utils.settings import bb_cfg


class Libtiff(VProject):
    """Libtiff is a library for reading and writing Tagged Image File Format
    files."""

    NAME = 'libtiff'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.FILE_FORMAT

    SOURCE = [
        block_revisions([
            GoodBadSubgraph(["0ef31e1f62aa7a8b1c488a59c4930775ee0046e4"],
                            ["a63512c436c64ad94b8eff09d6d7faa7e638d45d"],
                            "Bug in Libtiff"),
            GoodBadSubgraph(["88df59e89cfb096085bc5299f087eaceda73f12e"], [
                "901535247413d30d9380ee837ecdb9fb661350c6",
                "5ef6de4c7055a3b426d97d5af1a77484ee92eb30"
            ], "Does not build"),
            GoodBadSubgraph(["6d46b8e4642f372192e94976576b13dcb89970d8"], [
                "88df59e89cfb096085bc5299f087eaceda73f12e"
            ], "Does not build because of libtool version discrepancy"),
            GoodBadSubgraph(["5cbfc68f0625d6c29d724b6e57fa7e98017ad325"],
                            ["59e0f5cb3316089eb81064efdc3ba0eac7145fab"],
                            "Bug in Libtiff"),
            SingleRevision(
                "614095e3d06f6ac95fc9bb2e9333cf95c228be1c", "Bug in Libtiff"
            ),
            SingleRevision(
                "a1caf14ce4640eec759a801ea601bd022bdc02d3", "Bug in Libtiff"
            ),
            GoodBadSubgraph(["f7aebc264761adc41142e98e2285700dc51d384e"], [
                "9f3e08cf9409573ffa67e243c8bfbf6263b0fcb5"
            ], "Issue on some machines, not sure whos fault it is"),
            GoodBadSubgraph(["97049062b9d1efa7b00d7a13bcf97365b57c937b"],
                            ["66eb5c7cd07fec0647517f418e5fc81c4e26d402"],
                            "Bug in Libtiff"),
            GoodBadSubgraph(["0769c447b7108fe616d855e1ba367ecbb90ba471"],
                            ["40c664948371d60908328f7ccb5982aebda1d04d"],
                            "Error in the Makefile of Libtiff"),
            GoodBadSubgraph(["0730d44a00a34db8659a16833453d231501722a7"],
                            ["5b60852fe65b5908130e809e1011b10afcaf1c9c"],
                            "Bub in Libtiff"),
            GoodBadSubgraph(["145eb81dc87441e400f2bdaf7b873c429ce8c768"],
                            ["0e40776b337855277cf8093cdc9fa1f838642be1"],
                            "Bug in Libtiff"),
            SingleRevision(
                "d7afc8c14f379f1e7dcf91d9c57cb9b2d1f2d926", "Bug in Libtiff"
            ),
            SingleRevision(
                "292c431e5d99464134255e7e2dc8d24fd6f797d5", "Bug in Libtiff"
            ),
            SingleRevision(
                "5b90af247ea3801ce93ec0922b8b81396caa885d", "Bug in Libtiff"
            ),
            SingleRevision(
                "45efaab3950e9aeb4bb6b697e5795613c629826c", "Bug in Libtiff"
            ),
            SingleRevision(
                "394965766478c9fb028b2bc2ca09e92a49a35f14", "Bug in Libtiff"
            ),
            SingleRevision(
                "0e3c0d0550dc5790779bd222844ac736d83e99a5", "Bug in Libtiff"
            ),
            SingleRevision(
                "d4bef27ee8361ee2d8aae6c30c7074d2547ee2f0", "Bug in Libtiff"
            )
        ])(
            PaperConfigSpecificGit(
                project_name="libtiff",
                remote="https://gitlab.com/libtiff/libtiff.git",
                local="libtiff",
                refspec="origin/HEAD",
                limit=None,
                shallow=False
            )
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', 'autoconf', 'autopoint', 'automake',
        'autotools-dev', 'libtool', 'pkg-config'
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Libtiff.NAME))

        binary_map.specify_binary(
            "libtiff/.libs/libtiff.so", BinaryType.SHARED_LIBRARY
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        libtiff_version_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        with local.cwd(libtiff_version_source):
            with local.env(CC=str(c_compiler)):
                bb.watch(local["./autogen.sh"])()
                configure = bb.watch(local["./configure"])
                configure()
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Libtiff", "Libtiff")]
