from benchbuild.experiment import Experiment
from benchbuild import extensions as ext
from benchbuild.extensions import RunWithTime, RuntimeExtension
from benchbuild.settings import CFG
from benchbuild.utils.actions import Step
from plumbum import local
from os import path

EnvVars = {
    "LLVM_COMPILER": "clang",
    "CFLAGS": "-fvara-handleRM=Commit",
    "CXXFLAGS": "-fvara-handleRM=Commit",
    "CC": "wllvm",
    "CXX": "wllvm++",
    "WLLVM_OUTPUT_FILE": path.join(CFG["tmp_dir"].value(),"wllvm.log"),
    "LLVM_CC_NAME": "clang",
    "LLVM_CXX_NAME": "clang++"
}

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
        project.runtime_extension = ext.RunWithTime(RuntimeExtension(project,
                self, config={'jobs': int(CFG["jobs"].value())}))

        project.EnvVars = EnvVars
        project_src = path.join(project.builddir, project.src_dir)

        def evaluate_preparation():
            with local.cwd("/"):
                scripts_src = path.join(local.path(str(CFG["env"]["path"].value()[0])).up(3), "tools/VaRA/tools/marker-region")

            prepare = local[scripts_src + "/prepare.sh"]
            project.src_dir = path.join(project.src_dir, "out")

            with local.cwd(project_src):
                prepare("-c", CFG["env"]["path"].value(), "-t", scripts_src)

        def evaluate_extraction():
            extract = local["extract-bc"]
            with local.env(**EnvVars):
                with local.cwd(path.join(project_src ,"out")):
                    extract(project.name)

        def evaluate_analysis():
            opt = local[path.join(str(CFG["env"]["path"].value()[0]), "opt")]
            yamlAdd = "-yaml-out-file=" + project.name + ".yaml"
            run_cmd = opt["-vara-CFR", yamlAdd, path.join(project_src, "out", project.name + ".bc")]
            with local.cwd(CFG["tmp_dir"].value()):
                run_cmd()

        actns = self.default_runtime_actions(project)
        actns.insert(len(actns)-4, Prepare(self, evaluate_preparation))
        actns.insert(len(actns)-1, Extract(self, evaluate_extraction))
        actns.insert(len(actns)-1, Analyse(self, evaluate_analysis))
        return actns
