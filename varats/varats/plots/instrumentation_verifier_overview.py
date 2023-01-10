import typing as tp
from collections import OrderedDict, defaultdict
from datetime import datetime

import matplotlib.pyplot as plt

import varats.paper.paper_config as PC
from varats.data.reports.instrumentation_verifier_report import (
    InstrVerifierReport,
)
from varats.experiment.experiment_util import VersionExperiment
from varats.paper_mgmt.case_study import get_revisions_status_for_case_study
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.report.report import FileStatusExtension, BaseReport
from varats.revision.revisions import get_all_revisions_files
from varats.ts_utils.click_param_types import REQUIRE_EXPERIMENT_TYPE
from varats.utils.git_util import FullCommitHash, ShortCommitHash


class InstrumentationOverviewPlot(
    Plot, plot_name="instrumentation_overview_plot"
):

    def plot(self, view_mode: bool) -> None:
        self._generate_plot(**self.plot_kwargs)
        pass

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError

    def _generate_plot(self, **kwargs: tp.Any):
        current_config = PC.get_paper_config()
        experiment_type: tp.Type[VersionExperiment] = kwargs['experiment_type']

        projects: tp.Dict[str, tp.Dict[int, tp.List[tp.Tuple[
            ShortCommitHash, FileStatusExtension]]]] = OrderedDict()

        projects = {
            case_study.project_name:
            get_revisions_status_for_case_study(case_study, experiment_type)
            for case_study in current_config.get_all_case_studies()
        }

        fig, ax = plt.subplots()

        labels = list(projects.keys())

        results = {label: [] for label in ["success", "blocked", "failed"]}

        for _, revisions in projects.items():
            revs_success = len([
                rev for (rev, status) in revisions
                if status == FileStatusExtension.SUCCESS
            ])
            revs_blocked = len([
                rev for (rev, status) in revisions
                if status == FileStatusExtension.BLOCKED
            ])
            revs_failed = len([
                rev for (rev, status) in revisions
                if status == FileStatusExtension.FAILED
            ])

            results["success"].append(revs_success)
            results["blocked"].append(revs_blocked)
            results["failed"].append(revs_failed)

        ax.bar(labels, results["success"], label="Success")
        ax.bar(labels, results["blocked"], label="Blocked")
        ax.bar(labels, results["failed"], label="Failed")

        ax.set_ylabel("Number of revisions")
        ax.legend()

        reports = self._parse_trace_files(**kwargs)
        for r in reports:
            print(r)

    def _parse_trace_files(self, **kwargs: tp.Any):
        current_config = PC.get_paper_config()
        experiment_type: tp.Type[VersionExperiment] = kwargs['experiment_type']
        result = []

        for case_study in current_config.get_all_case_studies():
            revision_files = get_all_revisions_files(
                case_study.project_name, experiment_type, only_newest=False
            )

            for revision_file in revision_files:
                result.append(InstrVerifierReport(revision_file.full_path()))

        return result


class PaperConfigOverviewGenerator(
    PlotGenerator,
    generator_name="iv-overview-plot",
    options=[REQUIRE_EXPERIMENT_TYPE]
):
    """Generates a single pc-overview plot for the current paper config."""

    def generate(self) -> tp.List[Plot]:
        return [
            InstrumentationOverviewPlot(self.plot_config, **self.plot_kwargs)
        ]
