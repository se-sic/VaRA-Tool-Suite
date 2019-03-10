from benchbuild.experiment import Experiment
from benchbuild.extensions import compiler, time, run, base
from benchbuild.settings import CFG
from plumbum import local


class RunWLLVM(base.Extension):
    def __call__(self, command, *args, **kwargs):
        with local.env(LLVM_COMPILER="clang", WLLVM_OUTPUT_FILE="{}".format(str(CFG["tmp_dir"]) / "wllvm.log")):
            from benchbuild.utils.cmd import wllvm
            res = self.call_next(wllvm, *args, **kwargs)
        return res


class RegionAnalyser(Experiment):

    NAME = "RegionAnalyser"

    def actions_for_project(self, project):
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM() \
            << time.RunWithTimeout()

        project.ldflags = ["-lTrace"]
        project.cflags = ["-fvara-handleRM=High", "-mllvm", "-vara-tracer"]

        actns = self.default_runtime_actions(project)
        return actns
