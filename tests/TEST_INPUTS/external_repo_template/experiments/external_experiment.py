"""Dummy external experiment for registry tests."""

from benchbuild import Project

from varats.data.reports.empty_report import EmptyReport
from varats.experiment.experiment_util import VersionExperiment
from varats.report.report import ReportSpecification


class ExternalExperiment(VersionExperiment, shorthand="EXT"):
    """Dummy external experiment."""

    NAME = "ExternalExperiment"
    REPORT_SPEC = ReportSpecification(EmptyReport)

    def actions_for_project(self, project: Project):
        return []
