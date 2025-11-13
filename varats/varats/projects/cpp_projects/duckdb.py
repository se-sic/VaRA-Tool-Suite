"""DuckDB project module."""
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
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class DuckDB(VProject):
    """DuckDB project."""

    NAME = "duckdb"
    GROUP = "cpp_projects"
    DOMAIN = ProjectDomains.DATABASE

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="duckdb",
            remote="https://github.com/duckdb/duckdb.git",
            local="duckdb",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List['ProjectBinaryWrapper']:
        binary_map = RevisionBinaryMap(get_local_project_repo(DuckDB.NAME))

        binary_map.specify_binary("build/release/duckdb", BinaryType.EXECUTABLE)
        binary_map.specify_binary(
            "build/release/benchmark/benchmark_runner", BinaryType.EXECUTABLE
        )

        return binary_map[revision]

    def compile(self) -> None:
        version_source = self.source_of(self.primary_source)

        cc_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        with local.cwd(version_source):
            with local.env(
                CC=str(cc_compiler),
                CXX=str(cxx_compiler),
                GEN="ninja",
                BUILD_BENCHMARK="1",
                BUILD_TPCH="1"
            ):
                make = local["make"]

                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    def recompile(self) -> None:
        self.compile()

    def run_tests(self) -> None:
        pass
