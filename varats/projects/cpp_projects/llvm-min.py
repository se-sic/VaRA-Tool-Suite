from os import symlink

from benchbuild.utils.download import with_git, Git
from plumbum import local, path

from varats.projects.cpp_projects.llvm import LLVM


@with_git("https://github.com/se-passau/VaRA.git", limit=100, refspec="HEAD")
class LLVMmin(LLVM):
    """ LLVM with LLD linker and Extra Clang tools """

    NAME = 'llvm-min'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)
    LLVM_VERS = "60"
    DEV = "-dev"

    def compile(self):
        self.download()

        with local.cwd(self.SRC_FILE):
            self.download_packages()
            LLVM.build(self)

    def download_packages(self):
        # LLVM
        Git("https://git.llvm.org/git/llvm.git", "llvm", self.VERSION,
            shallow_clone=False)

        with local.cwd("llvm"):
            with local.cwd("tools"):
                # Clang
                Git("https://git.llvm.org/git/clang.git", "clang",
                    shallow_clone=False)

                with local.cwd("clang/tools"):
                    # Clang extra tools
                    Git("https://git.llvm.org/git/clang-tools-extra.git",
                        "extra", "release_" + self.LLVM_VERS,
                        shallow_clone=False)

            path.local.LocalPath.mkdir(local.path("build"))

            symlink(local.cwd / local.path("tools/VaRA/utils/vara/builds"),
                    local.cwd / "build" / "build_cfg")
