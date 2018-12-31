from benchbuild.utils.download import with_git, Git
from plumbum import local

from varats.projects.cpp_projects.llvm import LLVM


@with_git("https://git.llvm.org/git/llvm.git", limit=100, refspec="HEAD")
class LLVMmin(LLVM):
    """ LLVM with LLD linker and Extra Clang tools """

    NAME = 'llvm-min'
    GROUP = 'llvm'
    SRC_FILE = NAME + "-{0}".format(LLVM.VERSION)
    DEV = "-dev"

    def compile(self):
        self.download()

        with local.cwd(self.SRC_FILE):
            self.download_packages()
            LLVM.build(self)

    def download_packages(self):
        with local.cwd("tools"):
            # Clang
            Git("https://git.llvm.org/git/clang.git", "clang",
                shallow_clone=False)

            with local.cwd("clang/tools"):
                # Clang extra tools
                Git("https://git.llvm.org/git/clang-tools-extra.git",
                    "extra", LLVM.VERSION, shallow_clone=False)
