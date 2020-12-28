"""Project file for redis."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper_mgmt.paper_config import project_filter_generator
from varats.project.project_util import (
    wrap_paths_to_binaries_with_name,
    ProjectBinaryWrapper,
    BinaryType,
)
from varats.provider.cve.cve_provider import CVEProviderHook
from varats.utils.settings import bb_cfg


class Redis(bb.Project, CVEProviderHook):  # type: ignore
    """
    Redis is an in-memory database that persists on disk.

    (fetched by Git)
    """

    NAME = 'redis'
    GROUP = 'c_projects'
    DOMAIN = 'database'

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/antirez/redis.git",
            local="redis",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("redis")
        )
    ]

    @property
    def binaries(self) -> tp.List[ProjectBinaryWrapper]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries_with_name([
            ('redis_server', 'src/redis-server', BinaryType.executable)
        ])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        redis_source = local.path(self.source_of_primary)

        clang = bb.compiler.cc(self)
        with local.cwd(redis_source):
            with local.env(CC=str(clang)):
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Redislabs", "Redis")]
