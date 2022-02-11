"""Project file for libpng."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make, cmake, mkdir
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


class Libpng(VProject):
    """
    Picture library.

    (fetched by Git)
    """

    NAME = 'libpng'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.FILE_FORMAT

    SOURCE = [
        block_revisions([
            GoodBadSubgraph(["8694cd8bf5f7d0d2739e503218eaf749c6cb7071"],
                            ["0e13545712dc39db5689452ff3299992fc0a8377"],
                            "missing generic libpng.so"),
            GoodBadSubgraph(["9d2ab7b40505c5e94a7783e80217b60f474488fe"],
                            ["b17c75b222942a31394e65c0c1da9fd7ec9f3a4c"],
                            "missing generic libpng.so"),
            GoodBadSubgraph(["0d5805822f8817a17937462a2fd0606ffdad378e"],
                            ["917648ecb92f45537924b3c46a4a811b956c7023"],
                            "build not atomatable"),
            GoodBadSubgraph(["917648ecb92f45537924b3c46a4a811b956c7023"], [
                "9d2ab7b40505c5e94a7783e80217b60f474488fe",
                "6611322a8b29103a160c971819f1c5a031cd9d4f"
            ], "cmake not available"),
            GoodBadSubgraph(["a04b5352310727f20b38e360006feeca94b7201f"],
                            ["0e13545712dc39db5689452ff3299992fc0a8377"],
                            "Not libpng"),
            GoodBadSubgraph(["e209df47c4b821f277504e0cc248d9022b639e55"],
                            ["d61b42c81d9d6f0905039ccc66870b2a27eafdd9"],
                            "Bug in Libpng"),
            GoodBadSubgraph(["8d9e494dfb208c88a9497038977b539310c7fca5"],
                            ["bf15ac7e86f4fc95b6b33831f212c3f13f955623"],
                            "Bug in Libpng"),
            GoodBadSubgraph(["7de02e722f8f6bdb2756e20091c42fa4ffaa89c1"],
                            ["45bb9a62ba343250497c33da2b0bad78376d55b8"],
                            "Bug in Libpng"),
            SingleRevision(
                "79b7e4e621fd611df658ec24a07080708fffe1de", "Bug in Libpng"
            ),
            SingleRevision(
                "67a289ffa924a00fab96a9bd6da8c069441138fa", "Bug in Libpng"
            ),
            GoodBadSubgraph(["b76ab1260d156a390a47f81c0ea6ef0524208b8e"],
                            ["e4f124e3352d63f7162ab7c1360a2db6d54f2ff2"],
                            "Bug in Libpng"),
            GoodBadSubgraph(["5bc90389bffa3cf3d2b8325bfac5c4344a206bc0"],
                            ["c35f888c46986093582f73cafcd7185472748e4b"],
                            "Bug in Libpng"),
            GoodBadSubgraph(["5b79cd52f440a7e1ce418f87b92b526765719c54"],
                            ["c4081f05c88d171cd476d5df78ed4a690296c602"],
                            "Bug in Libpng"),
            GoodBadSubgraph(["9c946e22fcad10c2a44c0380c0909da6732097ce"],
                            ["342c4eab2a0565de456f1f3efcc41b635544160e"],
                            "Bug in Libpng"),
            GoodBadSubgraph(["40afb685704f1a5bf8d9edc0b5c7ec7f25e94b77"],
                            ["619cf868e60807d759639cfb070987ad059fa0c9"],
                            "Bug in Libpng"),
            SingleRevision(
                "7c709f039f7ff3cc92eea03af0660a171ef0673d", "Bug in Libpng"
            ),
            SingleRevision(
                "3fa1df48a1c14d3004733471ce7fbce916750911", "Bug in Libpng"
            ),
            SingleRevision(
                "a1312f7b190df545fb7ec90e23cc4a9b6328af00", "Bug in Libpng"
            ),
            SingleRevision(
                "42369ccd85a48c0802093ecf02444cc4dfc4f1dd", "Bug in Libpng"
            ),
            SingleRevision(
                "d930d36155fe79b277c11d868572769cb4ffb586", "Bug in Libpng"
            ),
            SingleRevision(
                "6e8ba0fab666eb6c90e929988e8fb3439449e7f9", "Bug in Libpng"
            ),
            SingleRevision(
                "ad41b8838a91ab36880716c2264f70ef4651b89f", "Bug in Libpng"
            ),
            GoodBadSubgraph(["d332c67da7818132e462fc44ec28b0b7420bc5b5"],
                            ["1d7f56ab64f397d5841cc277fae7aeaac44ac088"],
                            "Bug in Libpng"),
            SingleRevision(
                "db67cba8d42f5f13a96ce6080a61567f66afd915", "Bug in Libpng"
            ),
            SingleRevision(
                "c9e27d026de520a8646f8f5ee6d20a4080d258b6", "Bug in Libpng"
            ),
            SingleRevision(
                "7b9796539d8d15a61f2aa495fd23fbd5b4a90335", "Bug in Libpng"
            ),
            GoodBadSubgraph(["05a4db1fcd776931bbba0c3472ada94014c3a395"], [
                "403636577395221e63e27b69c5546ae6606f4fa2",
                "2e7c3a6e706e8d3cb54587c2bf8b3b3fdc30ae5a"
            ], "Bug in Libpng"),
            SingleRevision(
                "6cae24c265ea7a3d19a1655b0f7692ada4273290", "Bug in Libpng"
            ),
            SingleRevision(
                "04336ba10ff4da8b69292f6c936c4c0d7bbe67c7", "Bug in Libpng"
            )
        ])(
            PaperConfigSpecificGit(
                project_name="libpng",
                remote="https://github.com/glennrp/libpng.git",
                local="libpng",
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
        binary_map = RevisionBinaryMap(get_local_project_git_path(Libpng.NAME))

        binary_map.specify_binary('build/libpng.so', BinaryType.SHARED_LIBRARY)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        libpng_source = local.path(self.source_of(self.primary_source))

        compiler = bb.compiler.cc(self)
        mkdir(libpng_source / "build")
        with local.cwd(libpng_source / "build"):
            with local.env(CC=str(compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
        with local.cwd(libpng_source):
            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Libpng", "Libpng")]
