"""Project file for mongodb."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import python3
from benchbuild.utils.revision_ranges import RevisionRange
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_repo,
    verify_binaries,
    RevisionBinaryMap,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import (
    ShortCommitHash,
    FullCommitHash,
    typed_revision_range,
    RepositoryHandle,
)
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

    _SCONS_REVISIONS = RevisionRange(
        "e73188b5512c82290a4070af4afddac20d0b981e",
        "6e26f553f512d862a16099deeda11e5d8437d86c"
    )
    _BAZEL_REVISIONS = RevisionRange(
        "230828c095dccb1e04aeb5ebd0ba632461e13b4c", "HEAD"
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(MongoDB.NAME))

        # TODO: please add correct binary names
        binary_map.specify_binary(
            "bazel-bin/install-mongod/bin/mongod",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange(
                "230828c095dccb1e04aeb5ebd0ba632461e13b4c", "HEAD"
            )
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        mongodb_version_source = local.path(self.source_of(self.primary_source))
        mongodb_revision = ShortCommitHash(self.version_of_primary)
        repo_handle = RepositoryHandle(mongodb_version_source)

        self._SCONS_REVISIONS.init_cache(mongodb_version_source)
        self._BAZEL_REVISIONS.init_cache(mongodb_version_source)

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)
        with local.cwd(mongodb_version_source):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                if mongodb_revision in typed_revision_range(
                    repo_handle, self._SCONS_REVISIONS, ShortCommitHash
                ):
                    bb.watch(python3)(
                        "buildscripts/scons.py",
                        f"-j {get_number_of_jobs(bb_cfg())}", "-d",
                        "--disable-warnings-as-errors"
                    )
                elif mongodb_revision in typed_revision_range(
                    repo_handle, self._BAZEL_REVISIONS, ShortCommitHash
                ):
                    # While MongoDB has their own install script for bazel, it
                    # does not work properly in our build environments as it installs
                    # to the users home directory which e.g. is not available on cluster nodes.
                    # Thus, we assume that bazel is already installed and can be found in PATH.
                    bazel = local["bazel"]
                    bazel = bazel["build", "install-mongod"]

                    bb.watch(bazel)()
                else:
                    raise RuntimeError(
                        f"MongoDB revision {mongodb_revision} is not in "
                        "known build system revision ranges."
                    )

            verify_binaries(self)

    def recompile(self) -> None:
        # Should be the same as compile for MongoDB
        self.compile()

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Mongodb", "Mongodb")]
