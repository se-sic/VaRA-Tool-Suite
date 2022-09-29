"""Example table that uses different workloads and visualizes the time it took
to run them."""
import typing as tp

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.report.gnu_time_report import WLTimeReportAggregate
from varats.revision.revisions import get_processed_revisions_files
from varats.ts_utils.click_param_types import REQUIRE_MULTI_EXPERIMENT_TYPE
from varats.utils.git_util import FullCommitHash


class TimedWorkloadPlot(Plot, plot_name="timed_workload"):
    """Plot to visualize code churn for a git repository."""

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        df = pd.DataFrame()

        if len(self.plot_kwargs["experiment_type"]) > 1:
            print(
                "Plot can currently only handle a single experiment, "
                "ignoring everything else."
            )

        for case_study in case_studies:
            project_name = case_study.project_name

            report_files = get_processed_revisions_files(
                project_name, self.plot_kwargs["experiment_type"][0],
                WLTimeReportAggregate,
                get_case_study_file_name_filter(case_study)
            )

            for report_filepath in report_files:
                agg_time_report = WLTimeReportAggregate(
                    report_filepath.full_path()
                )
                report_file = agg_time_report.filename

                for workload_name in agg_time_report.workload_names():
                    for wall_clock_time in \
                            agg_time_report.measurements_wall_clock_time(
                        workload_name
                    ):
                        unique_reference = (
                            f"{project_name}-"
                            f"{report_file.binary_name}"
                            f"-{str(report_file.commit_hash)}"
                        )
                        new_row = {
                            "Project-Binary-Revision": unique_reference,
                            "Workload": workload_name,
                            "Revision": str(report_file.commit_hash),
                            "Mean wall time (msecs)": wall_clock_time * 1000,
                        }

                        df = df.append(new_row, ignore_index=True)

        fig, ax = plt.subplots()
        fig.set_size_inches(11.7, 8.27)
        sns.boxplot(
            x="Workload",
            y="Mean wall time (msecs)",
            hue="Project-Binary-Revision",
            data=df,
            ax=ax,
        )
        sns.despine()

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class TimedWorkloadPlotGenerator(
    PlotGenerator,
    generator_name="time-workloads",
    options=[REQUIRE_MULTI_EXPERIMENT_TYPE]
):
    """Generates repo-churn plot(s) for the selected case study(ies)."""

    def generate(self) -> tp.List[Plot]:
        return [TimedWorkloadPlot(self.plot_config, **self.plot_kwargs)]
