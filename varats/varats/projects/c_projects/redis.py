"""Project file for redis."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
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


class Redis(VProject):
    """
    Redis is an in-memory database that persists on disk.

    (fetched by Git)
    """

    NAME = 'redis'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.DATABASE

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="redis",
            remote="https://github.com/antirez/redis.git",
            local="redis",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Redis.NAME))

        binary_map.specify_binary(
            'src/redis-server',
            BinaryType.EXECUTABLE,
            override_binary_name='redis_server'
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        redis_source = local.path(self.source_of_primary)

        clang = bb.compiler.cc(self)
        with local.cwd(redis_source):
            with local.env(CC=str(clang)):
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Redislabs", "Redis")]
