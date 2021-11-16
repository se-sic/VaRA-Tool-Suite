"""Project file for the GNU coreutils."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import git, make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper_mgmt.paper_config import project_filter_generator
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    wrap_paths_to_binaries,
    ProjectBinaryWrapper,
    BinaryType,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class Coreutils(VProject):
    """GNU coretuils / UNIX command-line tools (fetched by Git)"""

    NAME = 'coreutils'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/coreutils/coreutils.git",
            local="coreutils",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("coreutils")
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([
            # figure out how to handle this file correctly in filenames
            # 'src/[',
            ('src/uniq', BinaryType.EXECUTABLE),
            ('src/dircolors', BinaryType.EXECUTABLE),
            ('src/numfmt', BinaryType.EXECUTABLE),
            ('src/b2sum', BinaryType.EXECUTABLE),
            ('src/mv', BinaryType.EXECUTABLE),
            ('src/fold', BinaryType.EXECUTABLE),
            ('src/dir', BinaryType.EXECUTABLE),
            ('src/mkfifo', BinaryType.EXECUTABLE),
            ('src/vdir', BinaryType.EXECUTABLE),
            ('src/sha512sum', BinaryType.EXECUTABLE),
            ('src/unexpand', BinaryType.EXECUTABLE),
            ('src/join', BinaryType.EXECUTABLE),
            ('src/nproc', BinaryType.EXECUTABLE),
            ('src/ptx', BinaryType.EXECUTABLE),
            ('src/printf', BinaryType.EXECUTABLE),
            ('src/ginstall', BinaryType.EXECUTABLE),
            ('src/du', BinaryType.EXECUTABLE),
            ('src/printenv', BinaryType.EXECUTABLE),
            # 'dcgen', was not found in version #961d668
            ('src/groups', BinaryType.EXECUTABLE),
            ('src/sync', BinaryType.EXECUTABLE),
            ('src/ln', BinaryType.EXECUTABLE),
            ('src/shuf', BinaryType.EXECUTABLE),
            ('src/false', BinaryType.EXECUTABLE),
            ('src/mkdir', BinaryType.EXECUTABLE),
            ('src/chmod', BinaryType.EXECUTABLE),
            ('src/link', BinaryType.EXECUTABLE),
            ('src/cat', BinaryType.EXECUTABLE),
            ('src/pwd', BinaryType.EXECUTABLE),
            ('src/chown', BinaryType.EXECUTABLE),
            ('src/head', BinaryType.EXECUTABLE),
            ('src/sleep', BinaryType.EXECUTABLE),
            ('src/fmt', BinaryType.EXECUTABLE),
            ('src/getlimits', BinaryType.EXECUTABLE),
            ('src/test', BinaryType.EXECUTABLE),
            ('src/paste', BinaryType.EXECUTABLE),
            ('src/comm', BinaryType.EXECUTABLE),
            ('src/mknod', BinaryType.EXECUTABLE),
            ('src/kill', BinaryType.EXECUTABLE),
            ('src/sha384sum', BinaryType.EXECUTABLE),
            ('src/sort', BinaryType.EXECUTABLE),
            ('src/sum', BinaryType.EXECUTABLE),
            ('src/sha224sum', BinaryType.EXECUTABLE),
            ('src/expand', BinaryType.EXECUTABLE),
            ('src/basenc', BinaryType.EXECUTABLE),
            ('src/truncate', BinaryType.EXECUTABLE),
            ('src/dd', BinaryType.EXECUTABLE),
            ('src/tail', BinaryType.EXECUTABLE),
            ('src/df', BinaryType.EXECUTABLE),
            ('src/tee', BinaryType.EXECUTABLE),
            ('src/tsort', BinaryType.EXECUTABLE),
            ('src/yes', BinaryType.EXECUTABLE),
            ('src/sha1sum', BinaryType.EXECUTABLE),
            ('src/rm', BinaryType.EXECUTABLE),
            ('src/make-prime-list', BinaryType.EXECUTABLE),
            ('src/logname', BinaryType.EXECUTABLE),
            ('src/pathchk', BinaryType.EXECUTABLE),
            ('src/whoami', BinaryType.EXECUTABLE),
            ('src/wc', BinaryType.EXECUTABLE),
            ('src/basename', BinaryType.EXECUTABLE),
            ('src/nohup', BinaryType.EXECUTABLE),
            # 'libstdbuf.so', could not find in version #961d668
            ('src/chroot', BinaryType.EXECUTABLE),
            ('src/users', BinaryType.EXECUTABLE),
            ('src/csplit', BinaryType.EXECUTABLE),
            # 'stdbuf',  is no tool
            ('src/hostid', BinaryType.EXECUTABLE),
            ('src/readlink', BinaryType.EXECUTABLE),
            ('src/timeout', BinaryType.EXECUTABLE),
            ('src/base64', BinaryType.EXECUTABLE),
            ('src/id', BinaryType.EXECUTABLE),
            ('src/nl', BinaryType.EXECUTABLE),
            ('src/stat', BinaryType.EXECUTABLE),
            ('src/cp', BinaryType.EXECUTABLE),
            ('src/shred', BinaryType.EXECUTABLE),
            ('src/who', BinaryType.EXECUTABLE),
            ('src/tr', BinaryType.EXECUTABLE),
            ('src/echo', BinaryType.EXECUTABLE),
            ('src/date', BinaryType.EXECUTABLE),
            ('src/split', BinaryType.EXECUTABLE),
            ('src/seq', BinaryType.EXECUTABLE),
            ('src/md5sum', BinaryType.EXECUTABLE),
            ('src/env', BinaryType.EXECUTABLE),
            ('src/expr', BinaryType.EXECUTABLE),
            ('src/true', BinaryType.EXECUTABLE),
            ('src/chcon', BinaryType.EXECUTABLE),
            ('src/chgrp', BinaryType.EXECUTABLE),
            ('src/mktemp', BinaryType.EXECUTABLE),
            ('src/unlink', BinaryType.EXECUTABLE),
            ('src/uname', BinaryType.EXECUTABLE),
            ('src/pinky', BinaryType.EXECUTABLE),
            ('src/stty', BinaryType.EXECUTABLE),
            ('src/rmdir', BinaryType.EXECUTABLE),
            ('src/ls', BinaryType.EXECUTABLE),
            ('src/runcon', BinaryType.EXECUTABLE),
            ('src/nice', BinaryType.EXECUTABLE),
            # 'blake2', is a folder
            ('src/tty', BinaryType.EXECUTABLE),
            ('src/factor', BinaryType.EXECUTABLE),
            ('src/tac', BinaryType.EXECUTABLE),
            ('src/realpath', BinaryType.EXECUTABLE),
            ('src/pr', BinaryType.EXECUTABLE),
            ('src/sha256sum', BinaryType.EXECUTABLE),
            # 'du-tests', removed due to bash script
            ('src/cksum', BinaryType.EXECUTABLE),
            ('src/touch', BinaryType.EXECUTABLE),
            ('src/cut', BinaryType.EXECUTABLE),
            ('src/od', BinaryType.EXECUTABLE),
            ('src/base32', BinaryType.EXECUTABLE),
            ('src/uptime', BinaryType.EXECUTABLE),
            ('src/dirname', BinaryType.EXECUTABLE),
        ])

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
