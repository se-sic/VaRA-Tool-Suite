"""
Project file for the GNU coreutils.
"""
from benchbuild.settings import CFG
from benchbuild.utils.cmd import make, git, mv
from benchbuild.utils.compiler import cc
from benchbuild.utils.download import with_git
from benchbuild.utils.run import run
import benchbuild.project as prj

from plumbum import local

from varats.paper.paper_config import project_filter_generator


@with_git(
    "https://github.com/coreutils/coreutils.git",
    limit=200,
    refspec="HEAD",
    shallow_clone=False,
    version_filter=project_filter_generator("coreutils"))
class Coreutils(prj.Project):  # type: ignore
    """ GNU coretuils / UNIX command-line tools (fetched by Git) """

    NAME = 'coreutils'
    GROUP = 'c_projects'
    DOMAIN = 'utils'
    VERSION = 'HEAD'
    # Names of the individual coreutil binaries
    BIN_NAMES = [
        'uniq', 'dircolors', 'numfmt', 'b2sum', 'mv', 'fold', 'dir', 'mkfifo',
        'vdir', 'sha512sum', 'unexpand', 'join', 'nproc', 'ptx', 'printf',
        'ginstall', 'du', 'printenv', 'dcgen', 'groups', 'sync', 'ln', 'shuf',
        'false', 'mkdir', 'chmod', 'link', 'cat', 'pwd', 'chown', 'head',
        'sleep', 'fmt', 'getlimits', 'test', 'paste', 'comm', 'mknod', 'kill',
        'sha384sum', 'sort', 'sum', 'sha224sum', 'expand', 'basenc',
        'truncate', 'dd', 'tail', 'df', 'tee', 'tsort', 'yes', 'sha1sum',
        '.deps', 'rm', 'make-prime-list', 'logname', 'pathchk', 'whoami', 'wc',
        'basename', 'nohup', 'libstdbuf.so', 'chroot', 'users', 'csplit',
        'stdbuf', 'hostid', 'readlink', 'timeout', 'base64', 'id', 'nl',
        'stat', 'cp', 'shred', 'who', 'tr', 'echo', 'date', 'split', 'seq',
        'md5sum', 'env', 'expr', '[', 'true', 'chcon', 'chgrp', 'mktemp',
        'unlink', 'uname', 'pinky', 'stty', 'rmdir', 'ls', 'runcon', 'nice',
        'blake2', 'blake2/.deps', 'tty', 'factor', 'tac', 'realpath', 'pr',
        'sha256sum', 'du-tests', 'cksum', 'touch', 'cut', 'od', 'base32',
        'uptime', 'dirname'
    ]
    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner: run) -> None:
        with local.cwd(self.SRC_FILE):
            run(make["-j", int(CFG["jobs"]), "check"])

    def compile(self) -> None:
        self.download()
        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            git("submodule", "init")
            git("submodule", "update")
            with local.env(CC=str(clang)):
                run(local["./bootstrap"])
                run(local["./configure"]["--disable-gcc-warnings"])
            run(make["-j", int(CFG["jobs"])])
