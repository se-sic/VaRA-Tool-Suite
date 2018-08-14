from benchbuild.experiment import Experiment
from benchbuild import extensions as ext
from benchbuild.extensions import RunWithTime, RuntimeExtension
from benchbuild.settings import CFG
import benchbuild.utils.actions as actions
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

CFG["vara"] = {
    "cfg": {
        "outfile": {
            "default": "source.yaml",
            "desc": "Path to store results of VaRA CFR analysis"
        }
    }
}


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
        project.runtime_extension = \
            RuntimeExtension(project, self) \
            << ext.RunWithTime()

        project.EnvVars = EnvVars

        def evaluate_extraction():
            extract = local["extract-bc"]
            project_src = path.join(project.builddir, project.src_dir)
            with local.env(**EnvVars):
                with local.cwd(project_src):
                    extract(project.name)

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
