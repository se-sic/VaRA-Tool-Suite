import typing as tp
from os import path

import benchbuild.utils.actions as actions
from benchbuild.extensions import compiler, run, time
from benchbuild.project import Project
from plumbum import local

from varats.data.report import FileStatusExtension as FSE
from varats.data.reports.empty_report import EmptyReport
from varats.experiments.wllvm import Extract, RunWLLVM
from varats.settings import bb_cfg
from varats.utils.experiment_util import (
    PEErrorHandler,
    UnlimitStackSize,
    VersionExperiment,
    get_default_compile_error_wrapped,
)


class PhasarTestAnalysis(actions.Step):  # type: ignore

    NAME = "PhasarTestAnalysis"
    DESCRIPTION = "TODO"

    RESULT_FOLDER_TEMPLATE = "{result_dir}/{project_dir}"

    def __init__(
        self,
        project: Project,
    ):
        super().__init__(obj=project, action_fn=self.analyze)

    def analyze(self) -> actions.StepResult:
        print("""
Wuhu running phasar


""")
        print(local.env["PATH"])

        phasar = local["phasar-llvm"]
        print(phasar("--help"))


class PhasarTest(VersionExperiment):

    NAME = "TestPhasar"

    REPORT_TYPE = EmptyReport

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM() \
            << run.WithTimeout()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            project, EmptyReport, PhasarTestAnalysis.RESULT_FOLDER_TEMPLATE
        )

        vara_result_folder = \
            f"{bb_cfg()['varats']['outfile']}/{project.name}"

        error_handler = PEErrorHandler(
            vara_result_folder,
            EmptyReport.get_file_name(
                project_name=str(project.name),
                binary_name="all",
                project_version=str(project.version),
                project_uuid=str(project.run_uuid),
                extension_type=FSE.CompileError,
                file_ext=".txt"
            )
        )

        analysis_actions = []

        # Check if all binaries have corresponding BC files
        all_files_present = True
        for binary in project.binaries:
            all_files_present &= path.exists(
                local.path(
                    Extract.BC_CACHE_FOLDER_TEMPLATE.format(
                        cache_dir=str(bb_cfg()["varats"]["result"]),
                        project_name=str(project.name)
                    ) + Extract.BC_FILE_TEMPLATE.format(
                        project_name=str(project.name),
                        binary_name=binary.name,
                        project_version=str(project.version)
                    )
                )
            )
        if not all_files_present:
            analysis_actions.append(actions.Compile(project))
            analysis_actions.append(Extract(project, handler=error_handler))

        analysis_actions.append(UnlimitStackSize(project))
        analysis_actions.append(PhasarTestAnalysis(project))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions
