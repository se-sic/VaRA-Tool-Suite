"""Project file for the GNU coreutils."""
import typing as tp
from pathlib import Path

import benchbuild.project as prj
from benchbuild.settings import CFG as BB_CFG
from benchbuild.utils.cmd import git, make
from benchbuild.utils.compiler import cc
from benchbuild.utils.download import with_git
from benchbuild.utils.run import run
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.data.provider.cve.cve_provider import CVEProviderHook
from varats.paper.paper_config import project_filter_generator
from varats.utils.project_util import (
    wrap_paths_to_binaries,
    ProjectBinaryWrapper,
)


@with_git(
    "https://github.com/coreutils/coreutils.git",
    refspec="HEAD",
    shallow_clone=False,
    version_filter=project_filter_generator("coreutils")
)
class Coreutils(prj.Project, CVEProviderHook):  # type: ignore
    """GNU coretuils / UNIX command-line tools (fetched by Git)"""

    NAME = 'coreutils'
    GROUP = 'c_projects'
    DOMAIN = 'utils'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)

    @property
    def binaries(self) -> tp.List[ProjectBinaryWrapper]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries([
            # figure out how to handle this file correctly in filenames
            # 'src/[',
            'src/uniq',
            'src/dircolors',
            'src/numfmt',
            'src/b2sum',
            'src/mv',
            'src/fold',
            'src/dir',
            'src/mkfifo',
            'src/vdir',
            'src/sha512sum',
            'src/unexpand',
            'src/join',
            'src/nproc',
            'src/ptx',
            'src/printf',
            'src/ginstall',
            'src/du',
            'src/printenv',
            # 'dcgen', was not found in version #961d668
            'src/groups',
            'src/sync',
            'src/ln',
            'src/shuf',
            'src/false',
            'src/mkdir',
            'src/chmod',
            'src/link',
            'src/cat',
            'src/pwd',
            'src/chown',
            'src/head',
            'src/sleep',
            'src/fmt',
            'src/getlimits',
            'src/test',
            'src/paste',
            'src/comm',
            'src/mknod',
            'src/kill',
            'src/sha384sum',
            'src/sort',
            'src/sum',
            'src/sha224sum',
            'src/expand',
            'src/basenc',
            'src/truncate',
            'src/dd',
            'src/tail',
            'src/df',
            'src/tee',
            'src/tsort',
            'src/yes',
            'src/sha1sum',
            'src/rm',
            'src/make-prime-list',
            'src/logname',
            'src/pathchk',
            'src/whoami',
            'src/wc',
            'src/basename',
            'src/nohup',
            # 'libstdbuf.so', could not find in version #961d668
            'src/chroot',
            'src/users',
            'src/csplit',
            # 'stdbuf',  is no tool
            'src/hostid',
            'src/readlink',
            'src/timeout',
            'src/base64',
            'src/id',
            'src/nl',
            'src/stat',
            'src/cp',
            'src/shred',
            'src/who',
            'src/tr',
            'src/echo',
            'src/date',
            'src/split',
            'src/seq',
            'src/md5sum',
            'src/env',
            'src/expr',
            'src/true',
            'src/chcon',
            'src/chgrp',
            'src/mktemp',
            'src/unlink',
            'src/uname',
            'src/pinky',
            'src/stty',
            'src/rmdir',
            'src/ls',
            'src/runcon',
            'src/nice',
            # 'blake2', is a folder
            'src/tty',
            'src/factor',
            'src/tac',
            'src/realpath',
            'src/pr',
            'src/sha256sum',
            # 'du-tests', removed due to bash script
            'src/cksum',
            'src/touch',
            'src/cut',
            'src/od',
            'src/base32',
            'src/uptime',
            'src/dirname',
        ])

    def run_tests(self, runner: run) -> None:
        with local.cwd(self.SRC_FILE):
            run(make["-j", get_number_of_jobs(BB_CFG), "check"])

    def compile(self) -> None:
        self.download()
        compiler = cc(self)
        with local.cwd(self.SRC_FILE):
            git("submodule", "init")
            git("submodule", "update")
            with local.env(CC=str(compiler)):
                run(local["./bootstrap"])
                run(local["./configure"]["--disable-gcc-warnings"])

            run(make["-j", get_number_of_jobs(BB_CFG)])
            for binary in self.binaries:
                if not Path("{binary}".format(binary=binary)).exists():
                    print("Could not find {binary}")

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("gnu", "coreutils")]
