"""Project file for cmark."""

import benchbuild as bb
from benchbuild.utils.cmd import cmake, make
from benchbuild.utils.revision_ranges import RevisionRange, block_revisions
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import ImageBase, get_base_image
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    BinaryType,
    ProjectBinaryWrapper,
    RevisionBinaryMap,
    get_local_project_repo,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class Cmark(VProject):
    """CommonMark parsing and rendering library and program in C."""

    NAME = 'cmark'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.PARSER

    SOURCE = [
        block_revisions(
            [
                RevisionRange(
                    "650ad87f35f4405a2ca8270d2b2835daa442e5f1",
                    "16794168a936feb7f25b3fdbdddf6c24b14a779a",
                    "No CMake build system",
                ),
            ]
        )(
            PaperConfigSpecificGit(
                project_name="cmark",
                remote="https://github.com/commonmark/cmark.git",
                local="cmark",
                refspec="origin/HEAD",
                limit=None,
                shallow=False,
            )
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_12).run(
        'apt', 'install', '-y', 'cmake'
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash,
    ) -> list[ProjectBinaryWrapper]:
        """Returns a list of binaries for the given revision."""
        binary_map = RevisionBinaryMap(get_local_project_repo(Cmark.NAME))

        binary_map.specify_binary(
            'build/src/cmark',
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange(
                "75e924d81e0001c5e298cd89c99ff87d7cf6c8fb", "HEAD"
            ),
        )
        binary_map.specify_binary(
            'build/src/stmd',
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange(
                "358925ec028bcdb312616ffebf427eda595896cd",
                "7da937e2aea109e42b5ce9d6c9fe2e4e9ec877fc",
            ),
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        """Run the tests for the project."""
        pass

    def compile(self) -> None:
        """Compile the project."""
        cmark_source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)
        build_folder = cmark_source / "build"
        build_folder.mkdir()
        with local.cwd(build_folder):
            with local.env(CC=str(c_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(cmark_source):
            verify_binaries(self)
