from benchbuild.project import Project
from benchbuild.utils.cmd import cmake
from benchbuild.utils.compiler import cxx
from benchbuild.utils.run import run
from plumbum import local, path


class LLVM(Project):
    """ LLVM superclass """

    NAME = 'llvm'
    DOMAIN = 'analysis'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner):
        pass

    def build(self):
        path.local.LocalPath.mkdir(local.path("build/dev"))

        with local.cwd("build/dev"):
            with local.env(CXXFLAGS="-O2 -g -fno-omit-frame-pointer",
                           CXX=str(cxx(self))):
                run(cmake("-G", "Ninja",
                          "-DLLVM_ENABLE_ASSERTIONS=ON",
                          "-DBUILD_SHARED_LIBS=ON",
                          "-DLLVM_TARGETS_TO_BUILD=X86", "../.."))
