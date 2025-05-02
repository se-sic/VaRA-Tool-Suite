"""Project file for nginx (based on toxcore's project file)."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import cmake, make, mkdir
from benchbuild.utils.revision_ranges import (
    block_revisions,
    GoodBadSubgraph,
    RevisionRange,
    SingleRevision,
)
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_git_path,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import (
    ShortCommitHash,
    RevisionBinaryMap,
    get_all_revisions_between,
)
from varats.utils.settings import bb_cfg


class Nginx(VProject):
    """NGINX is the world's most popular Web Server, high performance Load
        Balancer, Reverse Proxy, API Gateway and Content Cache."""

    NAME = 'nginx'
    GROUP = 'c_projects'
    # Is it appropriate to call NGINX a Unix tool?
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="nginx",
            remote="https://github.com/nginx/nginx",
            local="nginx",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10)

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Nginx.NAME))
        binary_map.specify_binary("objs/nginx", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        nginx_version_source = local.path(self.source_of_primary)

        # for debugging
        from pudb.remote import set_trace
        # set_trace(term_size=(140, 45))


        compiler = bb.compiler.cc(self)

        # What do I need this for?
        # mkdir(nginx_version_source)

        with local.cwd(nginx_version_source):
            with local.env(CC=str(compiler)):
                bb.watch(local["./auto/configure"])(
                    '--sbin-path=/usr/local/nginx/nginx',
                    '--conf-path=/usr/local/nginx/nginx.conf',
                    '--pid-path=/usr/local/nginx/nginx.pid',
                    '--with-http_ssl_module'
                ) # --with-pcre=../pcre2-10.39  --with-zlib=../zlib-1.3)

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        # The project’s actual name is ‘c-toxcore’.
        return [("nginx", "nginx")]
