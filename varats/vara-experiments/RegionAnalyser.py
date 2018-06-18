from benchbuild.experiment import Experiment
from benchbuild import extensions as ext
from benchbuild.extensions import RunWithTime, RuntimeExtension
from benchbuild.settings import CFG
from benchbuild.utils.downloader import Git
from benchbuild.utils.actions import Clean, Step, Configure, Build
from benchbuild.utils.cmd import make
from benchbuild.utils.run import run
from plumbum import local
from plumbum.path.utils import delete
import logging
from os import path

LOG = logging.getLogger(__name__)

EnvVars = {
    "LLVM_COMPILER": "clang",
    "CFLAGS": "-fvara-handleRM=High",
    "CXXFLAGS": "-fvara-handleRM=High",
    "CC": "wllvm",
    "CXX": "wllvm++",
    "WLLVM_OUTPUT_FILE": path.join(CFG["tmp_dir"].value(),"wllvm.log"),
    "LLVM_COMPILER_PATH": "/home/hellmich/git/llvm/build/dev/bin",
    "LLVM_CC_NAME": "clang",
    "LLVM_CXX_NAME": "clang++"
}

class RegionAnalyser(Experiment):

    NAME = "RegionAnalyser"

    def actions_for_project(self, project):
        project.runtime_extension = ext.RunWithTime(RuntimeExtension(project,
                self, config={'jobs': int(CFG["jobs"].value())}))

        project.ldflags = ["-lTrace"]
        project.cflags = ["-fvara-handleRM=High", "-mllvm", "-vara-tracer"]
        project.EnvVars = EnvVars

        actns = self.default_runtime_actions(project)
        return actns
