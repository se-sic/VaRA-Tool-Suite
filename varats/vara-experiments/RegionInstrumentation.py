from benchbuild.experiment import Experiment
from benchbuild import extensions as ext
from benchbuild.settings import CFG
from plumbum import local
from os import path

class RunWLLVM(ext.Extension):
    def __call__(self, command, *args, **kwargs):
        with local.env(LLVM_COMPILER="clang", WLLVM_OUTPUT_FILE="{}"
                       .format(path.join(str(CFG["tmp_dir"].value()), 
                       "wllvm.log"))):
            from benchbuild.utils.cmd import wllvm
            res = self.call_next(wllvm, *args, **kwargs)
        return res

class RegionAnalyser(Experiment):

    NAME = "RegionAnalyser"

    def actions_for_project(self, project):
        project.runtime_extension = ext.RuntimeExtension(project, self) \
            << ext.RunWithTime()
        
        project.compiler_extension = ext.RunCompiler(project, self) \
            << RunWLLVM() \
            << ext.RunWithTimeout()

        project.ldflags = ["-lTrace"]
        project.cflags = ["-fvara-handleRM=High", "-mllvm", "-vara-tracer"]

        actns = self.default_runtime_actions(project)
        return actns
