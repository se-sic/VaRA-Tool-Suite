from benchbuild.experiment import Experiment
from benchbuild import extensions as ext
from benchbuild.settings import CFG
from benchbuild.utils.actions import Step
from benchbuild.utils import actions
from benchbuild.utils.cmd import extract_bc, wllvm, opt
from plumbum import local
from os import path

CFG["vara"] = {
    "prepare" : {
        "default": "",
        "desc": "Path to the prepare script of Niederhuber in VaRA"
    },
    "outfile": {
        "default": "",
        "desc": "Path to store results of VaRA CFR analysis."
    }
}

class RunWLLVM(ext.Extension):
    def __cal__(self, command, *args, **kwargs):
        with local.env(LLVM_COMPILER="clang", LLVM_OUTPUT_FILE="{}".format(
                       path.join(str(CFG["tmp_dir"].value()), "wllvm.log"))):
            res = self.call_next(wllvm, *args, **kwargs)
        return res

class Prepare(Step):
    NAME = "PREPARE"
    DESCRIPTION = "Prepares the analysis by downloading the two required scripts: prepare.sh and annotate.sh"

class Extract(Step):
    NAME = "EXTRACT"
    DESCRIPTION = "Extract bitcode out of the execution file."

class Analyse(Step):
    NAME = "ANALYSE"
    DESCRIPTION = "Analyses the bitcode with VaRA."

class CommitAnnotationReport(Experiment):
    """Generates a commit annotation report of VaRA."""

    NAME = "CommitAnnotationReport"

    def actions_for_project(self, project):
        project.runtime_extension = ext.RuntimeExtension(project, self) \
            << ext.RunWithTime()

        project.compiler_extension = ext.RunCompiler(project, self) \
            << RunWLLVM() \
            << ext.RunWithTimeout()

        project.cflags = ["-fvara-handleRM=Commit"]

        project_src = path.join(project.builddir, project.src_dir)

        def evaluate_preparation():
            prepare = local["prepare.sh"]
            project.src_dir = path.join(project.src_dir, "out")

            with local.cwd(project_src):
                prepare("-c", str(CFG["env"]["path"].value()[0]), "-t", 
                        str(CFG["vara"]["prepare"].value()))

        def evaluate_extraction():
            with local.cwd(path.join(project_src ,"out")):
                extract_bc(project.name)

        def evaluate_analysis():
            outfile = "-yaml-out-file={}".format(
                CFG["vara"]["outfile"].value()) + "/" + str(project.name) + \
                    "-" + str(project.run_uuid) + ".yaml"
            run_cmd = opt["-vara-CFR", outfile, path.join(project_src, "out", 
                          project.name + ".bc")]
            run_cmd()

        return [
            actions.MakeBuildDir(project),
            actions.Prepare(project),
            actions.Download(project),
            Prepare(self, evaluate_preparation),
            actions.Configure(project),
            actions.Build(project),
            actions.Run(project),
            Extract(self, evaluate_extraction),
            Analyse(self, evaluate_analysis),
            actions.Clean(project)
        ]
