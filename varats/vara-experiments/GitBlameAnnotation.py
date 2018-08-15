from benchbuild.experiment import Experiment
from benchbuild import extensions as ext
from benchbuild.extensions import RunWithTime, RuntimeExtension, RunCompiler
from benchbuild.settings import CFG
import benchbuild.utils.actions as actions
from plumbum import local
from os import path

CFG["vara"] = {
    "cfg": {
        "outfile": {
            "default": "source.yaml",
            "desc": "Path to store results of VaRA CFR analysis"
        }
    }
}

class RunWLLVM(ext.Extension):
    def __call__(self, command, *args, **kwargs):
        with local.env(LLVM_COMPILER="clang"):
            from benchbuild.utils.cmd import wllvm
            res = self.call_next(wllvm, *args, **kwargs)
        return res


class Extract(actions.Step):
    NAME = "EXTRACT"
    DESCRIPTION = "Extract bitcode out of the execution file."


class Analyse(actions.Step):
    NAME = "ANALYSE"
    DESCRIPTION = "Analyses the bitcode with VaRA."


class GitBlameAnntotation(Experiment):
    """Git Blame Annotation of VaRA."""

    NAME = "GitBlameAnnotation"

    def actions_for_project(self, project):
        project.runtime_extension = RuntimeExtension(project, self) \
            << ext.RunWithTime()

        project.compiler_extension = RunCompiler(project, self) \
            << RunWLLVM() \
            << ext.RunWithTimeout()

        project.cflags = ["-fvara-GB"]

        def evaluate_extraction():
            from benchbuild.utils.cmd import extract_bc
            project_src = path.join(project.builddir, project.src_dir)
            with local.cwd(project_src):
                extract_bc(project.name)

        def evaluate_analysis():
            from benchbuild.utils.cmd import opt
            project_src = path.join(project.builddir, project.src_dir)
            run_cmd = opt["-vara-CFR",
                          "-yaml-out-file={outfile}".format(
                              outfile=CFG["vara"]["cfg"]["outfile"].value()),
                          path.join(project_src, project.name + ".bc")]
            run_cmd()

        actns = [
            actions.MakeBuildDir(project),
            actions.Prepare(project),
            actions.Download(project),
            actions.Configure(project),
            actions.Build(project),
            actions.Run(project),
            Extract(self, evaluate_extraction),
            Analyse(self, evaluate_analysis),
            actions.Clean(project)
        ]
        return actns
