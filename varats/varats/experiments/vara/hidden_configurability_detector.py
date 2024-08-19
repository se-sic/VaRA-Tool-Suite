import re
import typing as tp

from benchbuild.utils import actions
from benchbuild.utils.cmd import git
from plumbum import local

from varats.data.reports.hidden_configurability_report import (
    HiddenConfigurabilityReport,
)
from varats.experiment.experiment_util import (
    VersionExperiment,
    ExperimentHandle,
    create_new_success_result_filepath,
)
from varats.project.varats_project import VProject
from varats.tools.research_tools.vara import VaRA
from varats.utils.git_util import ChurnConfig


class HiddenConfigurabilityDetector(actions.ProjectStep):  #type: ignore
    """Detects hidden configurability points in the project."""

    NAME = "HiddenConfigurabilityDetector"

    project: VProject

    def __init__(self, project: VProject, experiment_handle: ExperimentHandle):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle

    def __call__(self) -> actions.StepResult:
        return self.analyze()

    def analyze(self) -> actions.StepResult:
        """This step detects hidden configurability points in the project."""
        binary = self.project.binaries[0]

        result_file = create_new_success_result_filepath(
            self.__experiment_handle, HiddenConfigurabilityReport, self.project,
            binary
        )

        project_directory = self.project.source_of_primary

        # Create a list of all C/CPP files in the project
        files = []

        churn_config = ChurnConfig.create_c_style_languages_config()
        file_pattern = re.compile(
            "|".join(churn_config.get_extensions_repr(r"^.*\.", r"$"))
        )

        with local.cwd(project_directory):
            files = [
                file for file in git(
                    "ls-tree",
                    "-r",
                    "--name-only",
                    "HEAD",
                ).splitlines() if file_pattern.match(file)
            ]

        # Run the HiddenConfigurabilityDetector
        hvf = local[VaRA.install_location() / "bin" / "hidden-variable-finder"]

        with local.cwd(project_directory):
            run_cmd = hvf[f"--report-file={result_file}",
                          f"--root-dir={project_directory}"]
            run_cmd = run_cmd[files]

            run_cmd()

        return actions.StepResult.OK


class FindHiddenConfigurationPoints(VersionExperiment, shorthand="HCP"):
    """Detects hidden configurability points in the project."""

    NAME = "FindHiddenConfigurationPoints"

    def actions_for_project(self, project: VProject) -> tp.List[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""
        # For now, we only run the HiddenConfigurabilityDetector
        # In a later improvement, one could compile the project once and use the
        # generated compile_commands.json to run the HiddenConfigurabilityDetector
        # only on the files that are actually compiled.

        return [HiddenConfigurabilityDetector(project, self.get_handle())]
