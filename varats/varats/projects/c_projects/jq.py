"""Project file for jq."""

import benchbuild as bb
from benchbuild.utils.cmd import autoreconf, git, make
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


class Jq(VProject):
    """Command-line JSON processor."""

    NAME = 'jq'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        block_revisions(
            [
                RevisionRange(
                    "eca89acee00faf6e9ef55d84780e6eeddf225e5c",
                    "a33c6f3df9d84baf7d2e299e2f0441afea2bd2ec",
                    "No autotools build system",
                ),
            ]
        )(
            PaperConfigSpecificGit(
                project_name="jq",
                remote="https://github.com/jqlang/jq.git",
                local="jq",
                refspec="origin/HEAD",
                limit=None,
                shallow=False,
            )
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_12).run(
        'apt',
        'install',
        '-y',
        'autoconf',
        'automake',
        'libtool',
        'bison',
        'flex',
        'git',
        'libonig-dev',
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash,
    ) -> list[ProjectBinaryWrapper]:
        """Returns a list of binaries for the given revision."""
        binary_map = RevisionBinaryMap(get_local_project_repo(Jq.NAME))

        binary_map.specify_binary('jq', BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        """Run the tests for the project."""
        pass

    def compile(self) -> None:
        """Compile the project."""
        jq_source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)
        with local.cwd(jq_source):
            configure_args = ["--disable-docs"]
            # Newer revisions ship oniguruma as a submodule, older ones use
            # the system library
            if (jq_source / ".gitmodules").exists():
                bb.watch(git)("submodule", "update", "--init")
                configure_args.append("--with-oniguruma=builtin")

            with local.env(CC=str(c_compiler)):
                bb.watch(autoreconf)("-i")
                bb.watch(local["./configure"])(*configure_args)

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)
