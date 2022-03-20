"""Project file for doxygen."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import cmake, cp, make
from benchbuild.utils.revision_ranges import block_revisions, GoodBadSubgraph
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local
from plumbum.path.utils import delete

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


class Doxygen(VProject):
    """Doxygen."""

    NAME = 'doxygen'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.DOCUMENTATION

    SOURCE = [
        block_revisions([
            # TODO: se-sic/VaRA#536
            GoodBadSubgraph(["a6238a4898e20422fe6ef03fce4891c5749b1553"],
                            ["cf936efb8ae99dd297b6afb9c6a06beb81f5b0fb"],
                            "Needs flex <= 2.5.4 and >= 2.5.33"),
            GoodBadSubgraph(["093381b3fc6cc1e97f0e737feca04ebd0cfe538d"],
                            ["cf936efb8ae99dd297b6afb9c6a06beb81f5b0fb"],
                            "Needs flex <= 2.5.4 and >= 2.5.33")
        ])(
            PaperConfigSpecificGit(
                project_name="doxygen",
                remote="https://github.com/doxygen/doxygen.git",
                local="doxygen",
                refspec="origin/HEAD",
                limit=None,
                shallow=False
            )
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Doxygen.NAME))

        binary_map.specify_binary('doxygen', BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        doxygen_source = local.path(self.source_of_primary)

        clangxx = bb.compiler.cxx(self)
        with local.cwd(doxygen_source):
            with local.env(CXX=str(clangxx)):
                delete("CMakeCache.txt")
                bb.watch(cmake)("-G", "Unix Makefiles", ".")
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            bb.watch(cp)("bin/doxygen", ".")

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("doxygen", "doxygen")]
