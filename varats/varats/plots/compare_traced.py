"""Example table that uses different workloads and visualizes the time it took
to run them."""
import typing as tp

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import numpy as np

from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.report.gnu_time_report import WLTimeReportAggregate
from varats.revision.revisions import get_processed_revisions_files
from varats.ts_utils.click_param_types import REQUIRE_MULTI_EXPERIMENT_TYPE
from varats.utils.git_util import FullCommitHash

# TODO: Is there a better way to include revisions of all workloads than to use
#        only_newest=False ?
# Maybe the result files are not defined correctly. We should be able to find
# the revision files for all workloads with only_newest=True...


class CompareRuntimesPlot(Plot, plot_name="compare_runtimes"):

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        df = pd.DataFrame()

        for case_study in case_studies:
            project_name = case_study.project_name
            print(project_name)

            for experiment in self.plot_kwargs["experiment_type"]:
                print(experiment.NAME)
                report_files = get_processed_revisions_files(
                    project_name,
                    experiment,
                    WLTimeReportAggregate,
                    get_case_study_file_name_filter(case_study),
                    only_newest=False
                )

                for report_filepath in report_files:
                    agg_time_report = WLTimeReportAggregate(
                        report_filepath.full_path()
                    )
                    report_file = agg_time_report.filename

                    for workload_name in agg_time_report.workload_names():
                        print(workload_name)
                        for wall_clock_time in \
                                agg_time_report.measurements_wall_clock_time(
                            workload_name
                        ):
                            new_row = {
                                "Binary":
                                    report_file.binary_name,
                                "Experiment":
                                    experiment.NAME,
                                "Mean wall time (msecs)":
                                    wall_clock_time * 1000,
                            }

                            df = pd.concat([df, pd.DataFrame([new_row])],
                                           ignore_index=True)
                            # df = df.append(new_row, ignore_index=True)

        fig, ax = plt.subplots()
        fig.set_size_inches(11.7, 8.27)
        sns.barplot(
            x="Binary",
            y="Mean wall time (msecs)",
            hue="Experiment",
            estimator=np.mean,
            data=df,
            ax=ax,
        )
        sns.despine()

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class CompareRuntimesPlotGenerator(
    PlotGenerator,
    generator_name="compare-runtimes",
    options=[REQUIRE_MULTI_EXPERIMENT_TYPE]
):

    def generate(self) -> tp.List[Plot]:
        return [CompareRuntimesPlot(self.plot_config, **self.plot_kwargs)]
