from benchbuild.utils.download import with_git, Git
from plumbum import local

from varats.projects.cpp_projects.llvm import LLVM


@with_git("https://git.llvm.org/git/llvm.git", limit=200, refspec="HEAD")
class LLVMall(LLVM):
    """ LLVM with all optional packages """

    NAME = 'llvm-all'
    GROUP = 'llvm'
    SRC_FILE = NAME + "-{0}".format(LLVM.VERSION)
    DEV = "-dev"

    def compile(self) -> None:
        self.download()

        with local.cwd(self.SRC_FILE):
            self.download_packages()
            LLVM.build(self)

    def download_packages(self) -> None:
        with local.cwd("projects"):
            # Compiler-RT
            Git("https://git.llvm.org/git/compiler-rt.git", "compiler-rt",
                LLVM.VERSION, shallow_clone=False)

            # OpenMP Library
            Git("https://github.com/llvm-mirror/openmp.git", "openmp",
                LLVM.VERSION, shallow_clone=False)

            # libcxxABI
            Git("https://github.com/llvm-mirror/libcxx.git", "libcxx",
                LLVM.VERSION, shallow_clone=False)
            Git("https://github.com/llvm-mirror/libcxxabi.git", "libcxxabi",
                LLVM.VERSION, shallow_clone=False)

            # Test suite
            Git("https://github.com/llvm-mirror/test-suite.git",
                "test-suite", LLVM.VERSION, shallow_clone=False)

        with local.cwd("tools"):
            # Clang
            Git("https://git.llvm.org/git/clang.git", "clang",
                shallow_clone=False)

            # LLD linker
            Git("https://git.llvm.org/git/lld.git", "lld",
                LLVM.VERSION, shallow_clone=False)

            with local.cwd("clang/tools"):
                # Clang extra tools
                Git("https://git.llvm.org/git/clang-tools-extra.git",
                    "extra", LLVM.VERSION, shallow_clone=False)

            # Polly loop optimizer
            Git("https://github.com/llvm-mirror/polly.git", "polly",
                LLVM.VERSION, shallow_clone=False)
