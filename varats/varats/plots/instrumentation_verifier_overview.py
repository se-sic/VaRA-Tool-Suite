import typing as tp
from collections import OrderedDict, defaultdict
from datetime import datetime

import matplotlib.pyplot as plt

import varats.paper.paper_config as PC
from varats.paper_mgmt.case_study import get_revisions_status_for_case_study
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.report.report import FileStatusExtension, BaseReport
from varats.ts_utils.click_param_types import REQUIRE_EXPERIMENT_TYPE
from varats.utils.git_util import FullCommitHash, ShortCommitHash


class InstrumentationOverviewPlot(
    Plot, plot_name="instrumentation_overview_plot"
):

    def plot(self, view_mode: bool) -> None:
        self._generate_plot()
        pass

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError

    def _generate_plot(self, experiment_type=None):
        print("Called generate plot")
        current_config = PC.get_paper_config()

        projects: tp.Dict[str, tp.Dict[int, tp.List[tp.Tuple[
            ShortCommitHash, FileStatusExtension]]]] = OrderedDict()

        projects = {
            case_study.project_name:
            get_revisions_status_for_case_study(case_study, experiment_type)
            for case_study in current_config.get_all_case_studies()
        }

        fig, ax = plt.subplots()

        labels = [projects.keys()]

        results = dict()

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
