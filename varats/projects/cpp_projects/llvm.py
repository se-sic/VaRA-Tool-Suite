from benchbuild.project import Project
from benchbuild.utils.cmd import cmake
from benchbuild.utils.compiler import cxx
from benchbuild.utils.download import with_git
from benchbuild.utils.run import run
from plumbum import local, path


@with_git("https://github.com/se-passau/VaRA.git", limit=100, refspec="HEAD")
class LLVM(Project):
    """ LLVM superclass """

    NAME = 'llvm'
    GROUP = 'code'
    DOMAIN = 'analysis'
    VERSION = 'HEAD'
    BIN_NAME = NAME

    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner):
        pass

    def build(self):
        path.local.LocalPath.mkdir(local.path("llvm/build/dev"))

        with local.cwd("llvm/build/dev"):
            with local.env(CXXFLAGS="-O2 -g -fno-omit-frame-pointer",
                           CXX=str(cxx(self))):
                run(cmake("-G", "Ninja",
                          "-DLLVM_ENABLE_ASSERTIONS=ON",
                          "-DBUILD_SHARED_LIBS=ON",
                          "-DLLVM_TARGETS_TO_BUILD=X86", "../.."))
