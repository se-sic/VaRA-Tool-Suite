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

class Extract(Step):
    NAME = "EXTRACT"
    DESCRIPTION = "Extract bitcode out of the execution file."

class Analyse(Step):
    NAME = "ANALYSE"
    DESCRIPTION = "Analyses the bitcode with VaRA."

class RegionAnalyser(Experiment):

    NAME = "RegionAnalyser"

    def actions_for_project(self, project):
        project.runtime_extension = ext.RunWithTime(RuntimeExtension(project,
                self, config={'jobs': int(CFG["jobs"].value())}))

        project_src = path.join(project.builddir, project.src_dir)

        def evaluate_extraction():
            extract = local["extract-bc"]
            with local.env(**EnvVars):
                extract(project.name)

        def evaluate_analysis():
            opt = local[path.join(EnvVars["LLVM_COMPILER_PATH"], "opt")]
            run_cmd = opt["-wllvm", "-vara-trace", path.join(project_src, project.name + ".bc")]
            with local.cwd(CFG["tmp_dir"].value()):
                run_cmd()

        actns = self.default_runtime_actions(project)
        for actn in actns:
            if "CLEAN" in actn.NAME:
                actns.remove(actn)

        actns.append(Configure(project))
        actns.append(Build(project))
        actns.append(Extract(self, evaluate_extraction))
        actns.append(Analyse(self, evaluate_analysis))
        actns.append(Clean(project))
        return actns
