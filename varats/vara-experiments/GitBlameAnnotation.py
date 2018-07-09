from benchbuild.experiment import Experiment
from benchbuild import extensions as ext
from benchbuild.extensions import RunWithTime, RuntimeExtension
from benchbuild.settings import CFG
from benchbuild.utils.actions import Step
from plumbum import local
from os import path

EnvVars = {
    "LLVM_COMPILER": "clang",
    "CFLAGS": "-fvara-GB",
    "CXXFLAGS": "-fvara-GB",
    "CC": "wllvm",
    "CXX": "wllvm++",
    "WLLVM_OUTPUT_FILE": path.join(str(CFG["tmp_dir"].value()), "wllvm.log"),
    "LLVM_CC_NAME": "clang",
    "LLVM_CXX_NAME": "clang++",
    "LLVM_COMPILER_PATH": path.join(str(CFG["env"]["path"].value()[0]), "bin/")
    # TODO: LLVM_COMP_PATH needs to be replaced with an better VaRA config option
}

class Extract(Step):
    NAME = "EXTRACT"
    DESCRIPTION = "Extract bitcode out of the execution file."

class Analyse(Step):
    NAME = "ANALYSE"
    DESCRIPTION = "Analyses the bitcode with VaRA."


class GitBlameAnntotation(Experiment):
    """Git Blame Annotation of VaRA."""

    NAME = "GitBlameAnnotation"

    def actions_for_project(self, project):
        project.runtime_extension = ext.RunWithTime(RuntimeExtension(project,
                self, config={'jobs': int(CFG["jobs"].value())}))

        project_src = path.join(project.builddir, project.src_dir)
        project.EnvVars = EnvVars

        def evaluate_extraction():
            extract = local["extract-bc"]
            with local.env(**EnvVars):
                with local.cwd(project_src):
                    extract(project.name)

        def evaluate_analysis():
            opt = local[path.join(str(CFG["env"]["path"].value()[0]),
                        "bin/opt")]
            run_cmd = opt["-vara-CFR", "-yaml-out-file=source.yaml",
                          path.join(project_src, project.name + ".bc")]
            with local.cwd(CFG["tmp_dir"].value()):
                run_cmd()

        actns = self.default_runtime_actions(project)
        actns.insert(len(actns)-1, Extract(self, evaluate_extraction))
        actns.insert(len(actns)-1, Analyse(self, evaluate_analysis))
        return actns
