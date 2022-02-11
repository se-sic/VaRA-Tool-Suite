"""Project file for mongodb."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import python3
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

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


class MongoDB(VProject):
    """
    MongoDB is a cross-platform document-oriented database program.

    Classified as a NoSQL database program, MongoDB uses JSON-like documents
    with optional schemas.
    """

    NAME = 'mongodb'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.DATABASE

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="mongodb",
            remote="https://github.com/mongodb/mongo.git",
            local="mongodb",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(MongoDB.NAME))

        # TODO: please add correct binary names
        binary_map.specify_binary("MISSING", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        mongodb_version_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)
        with local.cwd(mongodb_version_source):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(python3)(
                    "buildscripts/scons.py",
                    f"-j {get_number_of_jobs(bb_cfg())}", "-d",
                    "--disable-warnings-as-errors"
                )

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Mongodb", "Mongodb")]
