import os

import benchbuild.utils.actions as actions
from benchbuild.experiment import Experiment
from benchbuild.extensions import compiler, run, time
from benchbuild.settings import CFG
from benchbuild.utils.download import Git

from plumbum import local
from plumbum.path.utils import copy

CFG["em"] = {
    "results": {
        "default": "",
        "desc": "Path to the results of energy metering."
    },
    "results_rep": {
        "default": "",
        "desc": "Path to the repeated results of energy metering."
    }
}


class DownloadEM(actions.Step):
    NAME = "Energy_Metering"
    DESCRIPTION = "Measures the energy."


class AnalyseEM(actions.Step):
    NAME = "Energy_Metering"
    DESCRIPTION = "Measures the energy."


class EnergyMetering(Experiment):
    NAME = "EnergyMetering"

    def actions_for_project(self, project):
        project.runtime_extension = run.RuntimeExtension(project, self) \
                                    << time.RunWithTime()
        project.compiler_extension = compiler.RunCompiler(project, self)

        def download_em():
            with local.cwd(project.builddir):
                Git("https://github.com/se-passau/EnergyMetering.git",
                    self.NAME)
                Git("https://github.com/se-passau/EnergyMetering_CaseStudies.git",
                    "em_config")
            em_folder = project.builddir / "em_config" / project.name / "case-study"
            copy([em_folder / "summary-info",
                  em_folder / "summary-info-no-energy",
                  em_folder / "main.sh",
                  em_folder / "uiq2",
                  em_folder / "FeatureModel.xml",
                  em_folder / "configurations.csv",
                  em_folder / "config"], project.builddir / project.SRC_FILE)

        def evaluate_em():
            em_input = local.path(project.builddir) / project.SRC_FILE
            output_std = local.path(str(CFG["em"]["results"].value))
            output_rep = local.path(str(CFG["em"]["results_rep"].value))
            config = em_input / "config"

            em_initial = local[local.path(project.builddir) / self.NAME /
                               "em.sh"]
            em_output = local[output_std / "em.sh"]

            prepare = em_initial["prepare", "-d", output_std, "-c", config]
            prepare()

            start = em_output["start"]
            start()

            if os.path.exists(local.path(em_input / "repeat.map")):
                repeat = em_initial["-d", output_rep, "-r", output_std]
                repeat()
                start_rep = em_output["start"]
                start_rep()

            run(em_output["process-summary", "-i", em_input / "summary-info",
                          "-s", "summary.txt", "-D", "deviations.txt"])
            run(em_output["process-summary", "-i", em_input / "summary-info",
                          "-s", "measurements.csv", "-D", "deviations.csv",
                          "-C"])

        analysis_actions = [actions.Compile(project),
                            DownloadEM(self, download_em),
                            AnalyseEM(self, evaluate_em),
                            actions.Clean(project)]
        return analysis_actions
