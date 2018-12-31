import os

import benchbuild.utils.actions as actions
from benchbuild.experiment import Experiment
from benchbuild.extensions import compiler, run, time
from benchbuild.settings import CFG
from benchbuild.utils.download import Git
from plumbum import local

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

class Download_EM(actions.Step):
    NAME = "Energy_Metering"
    DESCRIPTION = "Measures the energy."

class Analyse_EM(actions.Step):
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

        def evaluate_em():
            input = local.path(project.builddir) / project.SRC_FILE
            output_std = local.path(str(CFG["em"]["results"].value))
            output_rep = local.path(str(CFG["em"]["results_rep"].value))
            config = input / "config"

            em_initial = local[local.path(project.builddir) / self.NAME /
                               "em.sh"]
            em_output = local[output_std / "em.sh"]

            prepare = em_initial["prepare", "-d", output_std, "-c", config]
            prepare()

            start = em_output["start"]
            start()

            if os.path.exists(local.path(input / "repeat.map")):
                repeat = em_initial["-d", output_rep, "-r", output_std]
                repeat()
                start_rep = em_output["start"]
                start_rep()

            em_output["process-summary", "-i", input / "summary-info", "-s",
                      "summary.txt", "-D", "deviations.txt"]
            em_output["process-summary", "-i", input / "summary-info", "-s",
                      "measurements.csv", "-D", "deviations.csv", "-C"]

        analysis_actions = []
        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(Download_EM(self, download_em))
        analysis_actions.append(Analyse_EM(self, evaluate_em))
        analysis_actions.append(actions.Clean(project))
        return analysis_actions
