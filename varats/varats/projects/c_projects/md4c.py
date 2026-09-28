"""Project file for md4c."""

import benchbuild as bb
from benchbuild.utils.cmd import cmake, make
from benchbuild.utils.revision_ranges import RevisionRange, SingleRevision
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


class Md4c(VProject):
    """Markdown parser for C (MD4C)."""

    NAME = 'md4c'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.PARSER

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="md4c",
            remote="https://github.com/mity/md4c.git",
            local="md4c",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
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
        binary_map = RevisionBinaryMap(get_local_project_repo(Md4c.NAME))

        binary_map.specify_binary(
            'build/md2html/md2html',
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange(
                "818dd3872681a8abdb451da418874786d03d8f58", "HEAD"
            ),
        )
        # The initial commit places all executables in the build root
        binary_map.specify_binary(
            'build/md2html',
            BinaryType.EXECUTABLE,
            only_valid_in=SingleRevision(
                "efed58af8eeb417e9251e3fc8ad260c4ce246614"
            ),
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        """Run the tests for the project."""
        pass

    def compile(self) -> None:
        """Compile the project."""
        md4c_source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)
        build_folder = md4c_source / "build"
        build_folder.mkdir()
        with local.cwd(build_folder):
            with local.env(CC=str(c_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(md4c_source):
            verify_binaries(self)
