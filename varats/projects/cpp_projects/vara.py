from benchbuild.project import Project
from benchbuild.utils.cmd import cmake
from benchbuild.utils.compiler import cxx
from benchbuild.utils.download import with_git
from benchbuild.utils.run import run
from plumbum import local, path


@with_git("https://github.com/se-passau/VaRA.git", limit=100, refspec="HEAD")
class VaRA(Project):
    """ VaRA """

    NAME = 'vara'
    GROUP = 'code'
    DOMAIN = 'analysis'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner):
        pass

    def compile(self):
        self.download()

        with local.cwd(self.SRC_FILE):
            run(local["./utils/vara/initVara.sh"])
            self.build()

    def build(self):
        path.local.LocalPath.mkdir(local.path("llvm/build/dev"))

        with local.cwd("llvm/build/dev"):
            with local.env(CXXFLAGS="-O2 -g -fno-omit-frame-pointer",
                           CXX=str(cxx(self))):
                cmake("-G", "Ninja",
                      "-DCMAKE_C_FLAGS_DEBUG=",
                      "-DCMAKE_CXX_FLAGS_DEBUG=",
                      "-DLLVM_ENABLE_ASSERTIONS=ON",
                      "-DBUILD_SHARED_LIBS=ON",
                      "-DLLVM_TARGETS_TO_BUILD=X86",
                      "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON", "../..")
