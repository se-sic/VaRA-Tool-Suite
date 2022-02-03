"""Project file for the GNU coreutils."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import git, make
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


class Coreutils(VProject):
    """GNU coretuils / UNIX command-line tools (fetched by Git)"""

    NAME = 'coreutils'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="coreutils",
            remote="https://github.com/coreutils/coreutils.git",
            local="coreutils",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(Coreutils.NAME)
        )

        binary_map.specify_binary('src/uniq', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/dircolors', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/numfmt', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/b2sum', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/mv', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/fold', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/dir', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/mkfifo', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/vdir', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/sha512sum', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/unexpand', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/join', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/nproc', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/ptx', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/printf', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/ginstall', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/du', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/printenv', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/groups', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/sync', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/ln', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/shuf', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/false', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/mkdir', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/chmod', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/link', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/cat', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/pwd', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/chown', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/head', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/sleep', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/fmt', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/getlimits', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/test', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/paste', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/comm', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/mknod', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/kill', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/sha384sum', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/sort', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/sum', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/sha224sum', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/expand', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/basenc', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/truncate', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/dd', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/tail', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/df', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/tee', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/tsort', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/yes', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/sha1sum', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/rm', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/make-prime-list', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/logname', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/pathchk', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/whoami', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/wc', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/basename', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/nohup', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/chroot', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/users', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/csplit', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/hostid', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/readlink', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/timeout', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/base64', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/id', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/nl', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/stat', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/cp', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/shred', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/who', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/tr', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/echo', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/date', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/split', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/seq', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/md5sum', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/env', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/expr', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/true', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/chcon', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/chgrp', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/mktemp', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/unlink', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/uname', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/pinky', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/stty', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/rmdir', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/ls', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/runcon', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/nice', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/tty', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/factor', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/tac', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/realpath', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/pr', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/sha256sum', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/cksum', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/touch', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/cut', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/od', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/base32', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/uptime', BinaryType.EXECUTABLE)
        binary_map.specify_binary('src/dirname', BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        coreutils_source = local.path(self.source_of_primary)
        with local.cwd(coreutils_source):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()), "check")

    def compile(self) -> None:
        coreutils_source = local.path(self.source_of_primary)
        compiler = bb.compiler.cc(self)
        with local.cwd(coreutils_source):
            git("submodule", "init")
            git("submodule", "update")
            with local.env(CC=str(compiler)):
                bb.watch(local["./bootstrap"])()
                bb.watch(local["./configure"])("--disable-gcc-warnings")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("gnu", "coreutils")]
