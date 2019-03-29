from os import symlink

from benchbuild.utils.download import with_git, Git
from plumbum import local, path

from varats.projects.cpp_projects.llvm import LLVM


@with_git("https://github.com/se-passau/VaRA.git", limit=100, refspec="HEAD")
class LLVMall(LLVM):
    """ LLVM with all optional packages """

    NAME = 'llvm-all'
    VERSION = 'HEAD'
    BIN_NAME = 'llvm'

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
            with local.cwd("projects"):
                # Compiler-RT
                Git("https://git.llvm.org/git/compiler-rt.git", "compiler-rt",
                    "release_" + self.LLVM_VERS, shallow_clone=False)

                # OpenMP Library
                Git("https://github.com/llvm-mirror/openmp.git", "openmp",
                    "release_" + self.VERSION, shallow_clone=False)

                # libcxxABI
                Git("https://github.com/llvm-mirror/libcxx.git", "libcxx",
                    "release_" + self.VERSION, shallow_clone=False)
                Git("https://github.com/llvm-mirror/libcxxabi.git", "libcxxabi",
                    "release_" + self.VERSION, shallow_clone=False)

                # Test suite
                Git("https://github.com/llvm-mirror/test-suite.git",
                    "test-suite", "release_" + self.VERSION,
                    shallow_clone=False)

            with local.cwd("tools"):
                # Clang
                Git("https://git.llvm.org/git/clang.git", "clang",
                    shallow_clone=False)

                # LLD linker
                Git("https://git.llvm.org/git/lld.git", "lld",
                    "release_" + self.LLVM_VERS, shallow_clone=False)

                with local.cwd("clang/tools"):
                    # Clang extra tools
                    Git("https://git.llvm.org/git/clang-tools-extra.git",
                        "extra", "release_" + self.LLVM_VERS,
                        shallow_clone=False)

                # Polly loop optimizer
                Git("https://github.com/llvm-mirror/polly.git", "polly",
                    "release_" + self.VERSION, shallow_clone=False)

            path.local.LocalPath.mkdir(local.path("build"))

            symlink(local.cwd / local.path("tools/VaRA/utils/vara/builds"),
                    local.cwd / "build" / "build_cfg")
