"""Performance interaction eval."""
import typing as tp

import pandas as pd
import seaborn as sns

from varats.base.configuration import PlainCommandlineConfiguration
from varats.paper.paper_config import get_loaded_paper_config, get_paper_config
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.tables.performance_interaction import (
    calculate_saved_costs,
    load_synth_baseline_data,
    load_synth_perf_inter_reports,
)
from varats.utils.config import load_configuration_map_for_case_study
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import FullCommitHash


class PerformanceInteractionSavingsPlot(Plot, plot_name="perf_inter_cost"):

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        data: tp.List[tp.Dict[str, tp.Any]] = []

        for case_study in case_studies:
            project_name = case_study.project_name

            configs = load_configuration_map_for_case_study(
                get_paper_config(), case_study, PlainCommandlineConfiguration
            )

            performance_data = load_synth_baseline_data(
                case_study, configs.ids()
            )

            if performance_data.empty:
                continue

            revisions = performance_data["revision"].unique().tolist()
            revisions.remove("base")
            performance_data = performance_data.pivot(
                index="config_id", columns="revision", values="wall_clock_time"
            )
            perf_inter_reports = load_synth_perf_inter_reports(case_study)

            for revision in revisions:
                perf_inter_report = perf_inter_reports.get(revision, None)

                savings = calculate_saved_costs(
                    project_name, revision, configs, perf_inter_report,
                    performance_data
                )

                data.append({
                    "project": project_name,
                    "revision": revision,
                    "abs_savings": savings[0],
                    "rel_savings": savings[1],
                    "time_savings": savings[2],
                })

        df = pd.DataFrame.from_records(data)
        sns.catplot(x="project", y="rel_savings", data=df)
        # fig = ax.get_figure()
        # fig.set_size_inches(20.92, 11.77)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class PerformanceInteractionSavings(
    PlotGenerator, generator_name="perf-inter-cost", options=[]
):

    def generate(self) -> tp.List[Plot]:
        return [
            PerformanceInteractionSavingsPlot(
                self.plot_config, **self.plot_kwargs
            )
        ]
