"""Project file for MariaDB."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    RevisionBinaryMap,
    get_local_project_repo,
    BinaryType,
    ProjectBinaryWrapper,
    default_cmake_compile,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class MariaDB(VProject):
    """MariaDB is a community-developed, commercially supported fork of the
    MySQL relational database management system (RDBMS), intended to remain free
    and open-source software under the GNU General Public License."""

    NAME = "mariadb"
    GROUP = "cpp_projects"
    DOMAIN = ProjectDomains.DATABASE

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="mariadb",
            remote="https://github.com/MariaDB/server",
            local="mariadb",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(MariaDB.NAME))

        # TODO: Add actual binaries when available
        binary_map.specify_binary("MISSING", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        default_cmake_compile(self)

    def recompile(self) -> None:
        version_source = self.source_of(self.primary_source)

        with local.cwd(version_source):
            make = local["make"]
            make("-j", get_number_of_jobs(bb_cfg()))
