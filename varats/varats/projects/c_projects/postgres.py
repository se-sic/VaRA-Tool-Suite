"""Project file for postgres."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    verify_binaries,
    RevisionBinaryMap,
    get_local_project_repo,
    BinaryType,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class PostgreSQL(VProject):
    """PostgreSQL is a powerful, open source object-relational database
    system."""

    NAME = "postgres"
    GROUP = "c_projects"
    DOMAIN = ProjectDomains.DATABASE

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="postgres",
            remote="https://github.com/postgres/postgres.git",
            local="postgres",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List['ProjectBinaryWrapper']:
        binary_map = RevisionBinaryMap(get_local_project_repo(PostgreSQL.NAME))

        binary_map.specify_binary("install/bin/postgres", BinaryType.EXECUTABLE)
        binary_map.specify_binary("install/bin/pgbench", BinaryType.EXECUTABLE)
        binary_map.specify_binary("install/bin/psql", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def compile(self) -> None:
        version_source = local.path(self.source_of_primary)

        cc_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        build_dir = version_source / "build"
        install_dir = version_source / "install"
        build_dir.mkdir(parents=True, exist_ok=True)
        install_dir.mkdir(parents=True, exist_ok=True)

        with local.cwd(build_dir):
            with local.env(CC=str(cc_compiler), CXX=str(cxx_compiler)):
                configure = local["../configure"]
                make = local["make"]

                bb.watch(configure)(f"--prefix={install_dir}")
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
                bb.watch(make)("install")

        with local.cwd(version_source):
            verify_binaries(self)

    def recompile(self) -> None:
        version_source = local.path(self.source_of_primary)
        build_dir = version_source / "build"

        with local.cwd(build_dir):
            make = local["make"]
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
            bb.watch(make)("install")

    def run_tests(self) -> None:
        pass
