import typing as tp

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.data.reports.dynamic_overhead_report import DynamicOverheadReport
from varats.revision.revisions import get_processed_revisions_files
from varats.ts_utils.click_param_types import REQUIRE_MULTI_EXPERIMENT_TYPE
from varats.utils.git_util import FullCommitHash


class DynamicOverheadPlot(Plot, plot_name="dynamic_overhead"):

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        df = pd.DataFrame()

        for case_study in case_studies:
            project_name = case_study.project_name

            for experiment in self.plot_kwargs["experiment_type"]:

                report_files = get_processed_revisions_files(
                    project_name,
                    experiment,
                    DynamicOverheadReport,
                    get_case_study_file_name_filter(case_study),
                    only_newest=False
                )


                for report_filepath in report_files:
                    report = DynamicOverheadReport(report_filepath.full_path())

                    new_row = {
                        "Name": report.filename.binary_name,
                        "Visited regions": report.regions_visited(),
                    }

                    df = pd.concat([df, pd.DataFrame([new_row])],
                                   ignore_index=True)

        fig, ax = plt.subplots()
        fig.set_size_inches(11.7, 8.27)
        sns.barplot(
            x="Name",
            y="Visited regions",
            hue="Name",
            data=df,
            ax=ax,
        )
        sns.despine()

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class DynamicOverheadPlotGenerator(
    PlotGenerator,
    generator_name="dynamic-overhead",
    options=[REQUIRE_MULTI_EXPERIMENT_TYPE]
):

    def generate(self) -> tp.List[Plot]:
        return [DynamicOverheadPlot(self.plot_config, **self.plot_kwargs)]
