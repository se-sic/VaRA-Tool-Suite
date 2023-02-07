"""Implements an empty experiment that just compiles the project."""
import os.path
import tempfile
import typing as tp
from pathlib import Path

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.utils.cmd import rm
from benchbuild.utils.cmd import mkdir, touch, time
from plumbum import local
from plumbum.cmd import rm, ls

from varats.data.reports.empty_report import EmptyReport
from varats.experiment.experiment_util import (
    VersionExperiment,
    ExperimentHandle,
    exec_func_with_pe_error_handler,
    get_default_compile_error_wrapped,
    create_default_analysis_failure_handler,
    get_varats_result_folder, ZippedReportFolder,
)
from varats.experiment.wllvm import RunWLLVM
from varats.report.gnu_time_report import TimeReport, TimeReportAggregate
from varats.report.report import FileStatusExtension as FSE
from varats.report.report import ReportSpecification


if __name__ == "__main__":
    with open("/scratch/messerig/varaRoot/results/xz/result_test.txt", "w") as f:
                                time_aggregate = TimeReportAggregate(Path("/scratch/messerig/varaRoot/results/xz/XZCompressionLevel6.zip"))
                                f.write(time_aggregate.summary)