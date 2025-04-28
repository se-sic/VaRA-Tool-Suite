import typing as tp

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from varats.data.reports.hidden_configurability_report import MPRTimeWLAggregate
from varats.experiments.vara.hidden_configurability_experiments import (
    TimePatchedWorkloads,
)
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.report.gnu_time_report import (
    WLTimeReportAggregate,
    TimeReportAggregate,
)
from varats.revision.revisions import get_processed_revisions_files


class ConfigurationOpportunitiesRuntimePlot(
    Plot, plot_name="configuration_opportunities_variation"
):
    """Plot that compares base runtimes for configuration opportunities with
    alternative values."""

    def plot(self, view_mode: bool) -> None:
        df = self.tabulate()

        if df.empty:
            return

        sns.stripplot(
            df, y="performance", x="config_opportunity", hue="variation"
        )

        baseline_performance = df[df["variation"] == "baseline"
                                 ]["performance"].mean()
        plt.axhline(
            y=baseline_performance,
            color='red',
            linestyle='--',
            linewidth=1,
            label="Baseline"
        )
        plt.legend().remove()
        plt.xticks(rotation=90)
        plt.ylabel("Runtime (s)")

    def tabulate(self) -> pd.DataFrame:
        case_study: CaseStudy = self.plot_kwargs['case_study']

        result_files = get_processed_revisions_files(
            case_study.project_name, TimePatchedWorkloads,
            TimePatchedWorkloads.report_spec().main_report,
            get_case_study_file_name_filter(case_study)
        )

        if len(result_files) == 0:
            print(f"No results found for {case_study.project_name}")
            return pd.DataFrame()

        # TODO: Properly handle multiple binaries/configurations
        if len(result_files) > 1:
            print(f"More than one result for {case_study.project_name}")

        report: MPRTimeWLAggregate = MPRTimeWLAggregate(
            result_files[0].full_path()
        )

        def extract_config_point(full_name: str) -> tp.Tuple[str, str]:
            # patch names follow the pattern "<patch_name>_<base_file_name>_<config_point>=<value>"
            # We are interested in the unique configuration points
            name_parts = full_name.split("_")
            config_point = name_parts[-1].split("=")
            return config_point[0], config_point[1].split('.')[0]

        def get_configuration_points(
            report_file: MPRTimeWLAggregate
        ) -> tp.List[str]:
            result = set()

            for patch_name in report_file.get_patch_names():
                # patch names follow the pattern "<patch_name>_<base_file_name>_<config_point>=<value>"
                # We are interested in the unique configuration points
                result.add(extract_config_point(patch_name)[0])

            return list(result)

        configuration_points = get_configuration_points(report)

        base_report: TimeReportAggregate = report.get_baseline_report()

        df: pd.DataFrame = pd.DataFrame()

        #TODO: Handle different workloads
        base_runtime = base_report.measurements_wall_clock_time

        table_rows = []

        for cp in configuration_points:
            table_rows.append({
                "config_opportunity": cp,
                "variation": "baseline",
                "performance": base_runtime
            })

        for patch_report in report.get_patched_reports():
            cp = extract_config_point(patch_report.filename.filename)
            table_rows.append({
                "config_opportunity": cp[0],
                "variation": cp[1],
                "performance": patch_report.measurements_wall_clock_time
            })

        df = pd.DataFrame.from_records(table_rows)
        df = df.explode('performance')

        return df


class ConfigurationOpportunitiesRuntimeGenerator(
    PlotGenerator,
    generator_name="configuration-opportunities-variation",
    options=[]
):
    """Generates the configuration opportunities runtime plot."""

    def generate(self) -> tp.List[Plot]:
        return [
            ConfigurationOpportunitiesRuntimePlot(
                self.plot_config, case_study=cs, **self.plot_kwargs
            ) for cs in get_loaded_paper_config().get_all_case_studies()
        ]
