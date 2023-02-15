"""Module for feature performance experiments that instrument and measure the
execution performance of each binary that is produced by a project."""
import os
import typing as tp

from pathlib import Path

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from plumbum import local
from plumbum.cmd import rm, ls, mv

from varats.experiment.experiment_util import (
    ExperimentHandle,
    get_varats_result_folder,
    VersionExperiment,
    get_default_compile_error_wrapped,
    get_varats_result_folder, ZippedReportFolder,
)
from varats.project.project_util import BinaryType
from varats.provider.feature.feature_model_provider import (
    FeatureModelProvider,
    FeatureModelNotFound,
)
from varats.report.report import ReportSpecification
from varats.report.report import FileStatusExtension as FSE
from varats.report.tef_report import TEFReport
from varats.report.tef_report import TEFReportAggregate


class ExecAndTraceBinary(actions.ProjectStep):  # type: ignore
    """Executes the specified binaries of the project, in specific
    configurations, against one or multiple workloads."""

    NAME = "xzWhiteboxAnalysis"
    DESCRIPTION = "Executes each binary and captures white-box " +\
        "performance traces."

    def __init__(self, project: Project, experiment_handle: ExperimentHandle):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle
    
    def __call__(self):
        #raise Exception()
        return self.run_perf_tracing()

    def run_perf_tracing(self) -> actions.StepResult:
        """Execute the specified binaries of the project, in specific
        configurations, against one or multiple workloads."""
        project: Project = self.project
        print(f"PWD {os.getcwd()}")

        number_of_repetition = 1

        vara_result_folder = get_varats_result_folder(project)
        for binary in project.binaries:
            if binary.type != BinaryType.EXECUTABLE:
                continue

            result_file = self.__experiment_handle.get_file_name(
                TEFReport.shorthand(),
                project_name=str(project.name),
                binary_name=binary.name,
                project_revision=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.SUCCESS
            )

            with local.cwd(local.path(project.source_of_primary)):
                with ZippedReportFolder(vara_result_folder / result_file.filename) as aggregated_time_reports_dir:
                    #Compression level 6 currently only, 6 is default

                    for compression_level in range(6, 7):
                        print(f"Currently at {local.path(project.source_of_primary)}")
                        print(f"Bin path {binary.path}")

                        # executable = local[f"{binary.path}"]
                        with ZippedReportFolder(
                                aggregated_time_reports_dir / Path(
                                    f"XZCompressionLevel{compression_level}")) as time_reports_dir:
                            with local.env(
                                VARA_TRACE_FILE=f"{vara_result_folder}/{result_file}"
                            ):

                                workload = "/scratch/messerig/varaRoot/experimentFiles/countries-land-1m.geo.json"
                                file_path_xz = "/scratch/messerig/varaRoot/experimentFiles/countries-land-1m.geo.json.xz"
                                rm_cmd = rm[file_path_xz]

                                for i in range(number_of_repetition):
                                    if Path(file_path_xz).is_file():
                                        rm_cmd()

                                    xz_cmd = binary[f"-{compression_level}", "-k", workload]
                                    xz_cmd()

                                    result_path = Path(time_reports_dir) / f"tefreport_compression_{compression_level}_{i}"

                                    #mv_cmd = mv[Path(vara_result_folder / result_file.filename), result_path]
                                    #mv_cmd()
                                    #tef_report = TEFReport(Path(time_reports_dir) /f"tefreport_compression_{compression_level}_{i}")
                                    #tef_report.feature_time_accumulator()

                                    #if result_path.is_file():
                                    #    rm_unparsed = rm[result_path]
                                    #    rm_unparsed()


                                    #executable("--slow")
                                    # executable()

                                    #if Path(file_path_xz).is_file():
                                    #    rm_cmd()
                        
                        #rename_file = mv[aggregated_time_reports_dir / Path("result_aggregate.json"), aggregated_time_reports_dir
                        #                 / Path(f"result_aggregate_{compression_level}.json")]
                        #rename_file()

        return actions.StepResult.OK
