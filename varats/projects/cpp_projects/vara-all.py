from os import symlink

from benchbuild.utils.cmd import git
from benchbuild.utils.download import with_git, Git
from plumbum import local, path

from varats.projects.cpp_projects.vara import VaRA


@with_git("https://github.com/se-passau/VaRA.git", limit=100, refspec="HEAD")
class VaRAall(VaRA):
    """ VaRA with all optional packages """

    NAME = 'vara-all'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)
    LLVM_VERS = "60"
    DEV = "-dev"

    def compile(self):
        self.download()

        with local.cwd(self.SRC_FILE):
            self.download_packages()
            VaRA.build(self)

    def download_packages(self):
        # LLVM
        Git("https://git.llvm.org/git/llvm.git", "llvm", self.VERSION,
            shallow_clone=False)

        with local.cwd("llvm"):
            self.git_add_remote("https://github.com/se-passau/vara-llvm.git")

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
                with local.cwd("clang"):
                    self.git_add_remote(
                        "https://github.com/se-passau/vara-clang.git")

                # LLD linker
                Git("https://git.llvm.org/git/lld.git", "lld",
                    "release_" + self.LLVM_VERS, shallow_clone=False)

                # VaRA
                Git("git@github.com:se-passau/VaRA.git", "VaRA",
                    "vara" + self.DEV, shallow_clone=False)

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

    def git_add_remote(self, url):
        git("remote", "add", "origin-vara", url)
        git("fetch", "origin-vara")
        git("checkout", "-f", "-b", "vara-" + self.LLVM_VERS + self.DEV,
            "origin-vara/vara-" + self.LLVM_VERS + self.DEV)
