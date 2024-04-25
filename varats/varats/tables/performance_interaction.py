"""Performance interaction eval."""
import ast
import logging
import typing as tp
from collections import defaultdict
from itertools import pairwise

import numpy as np
import pandas as pd

from varats.base.configuration import PlainCommandlineConfiguration
from varats.data.databases.performance_evolution_database import (
    PerformanceEvolutionDatabase,
)
from varats.data.metrics import ConfusionMatrix
from varats.experiments.vara.performance_interaction import (
    PerformanceInteractionExperiment,
)
from varats.jupyterhelper.file import load_performance_interaction_report
from varats.mapping.commit_map import get_commit_map, CommitMap
from varats.mapping.configuration_map import ConfigurationMap
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config, get_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.plots.performance_evolution import create_heatmap, rrs
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.cli_util import CLIOptionTy, make_cli_option
from varats.ts_utils.click_param_types import REQUIRE_CASE_STUDY
from varats.utils.config import load_configuration_map_for_case_study
from varats.utils.git_util import FullCommitHash, ShortCommitHash

LOG = logging.Logger(__name__)


class ConfusionMatrixData(tp.TypedDict):
    """Dict representing data for a confusion matrix."""

    actual_positive_values: tp.List[FullCommitHash]
    actual_negative_values: tp.List[FullCommitHash]
    predicted_positive_values: tp.List[FullCommitHash]
    predicted_negative_values: tp.List[FullCommitHash]


def is_regression(
    performance_data: pd.DataFrame,
    old_rev: ShortCommitHash,
    new_rev: ShortCommitHash,
    configs: ConfigurationMap,
    threshold: float,
    min_diff: float = 1
) -> tp.Tuple[bool, int]:
    """
    Calculates if there is a regression between two revisions.

    A regression exists if for at least one configuration the performance
    difference exceeds the threshold and is at least min_diff times greater than
    the standard deviation of the performance measurements.

    Args:
        performance_data: dataframe with the performance measurements for both
                          revisions and all configurations
        old_rev: old revision
        new_rev: new revision
        configs: configurations to consider
        threshold: percentage change that is considered a regression
        min_diff: factor that controls the minimum difference to the standard
                  deviation of the measurements

    Returns:
    """
    num_regressions = 0
    for cid in configs.ids():
        old_vals = ast.literal_eval(performance_data.loc[cid, old_rev])
        new_vals = ast.literal_eval(performance_data.loc[cid, new_rev])

        std_old = np.std(old_vals)
        std_new = np.std(new_vals)
        std = max(std_old, std_new)

        old_avg = np.average(old_vals)
        new_avg = np.average(new_vals)
        diff = abs(old_avg - new_avg)
        percent_change = diff / old_avg
        # times_std = diff / std

        if percent_change > threshold and diff > (min_diff * std):
            num_regressions += 1

    return num_regressions > 0, num_regressions


class PerformanceRegressionClassificationTable(Table, table_name="perf_reg"):
    """Table for performance regression classification analysis."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        thresholds = self.table_kwargs["threshold"]  # % diff
        min_diff = self.table_kwargs["sigma"]  # times std

        case_studies = get_loaded_paper_config().get_all_case_studies()

        data: tp.List[pd.DataFrame] = []
        for case_study in case_studies:
            project_name = case_study.project_name
            commit_map = get_commit_map(project_name)

            revisions = sorted(case_study.revisions, key=commit_map.time_id)

            configs = load_configuration_map_for_case_study(
                get_paper_config(), case_study, PlainCommandlineConfiguration
            )

            performance_data = \
                PerformanceEvolutionDatabase.get_data_for_project(
                project_name, ["revision", "config_id", "wall_clock_time"],
                commit_map,
                case_study,
                cached_only=True
            ).pivot(
                index="config_id", columns="revision", values="wall_clock_time"
            )

            perf_inter_report_files = get_processed_revisions_files(
                project_name,
                PerformanceInteractionExperiment,
                file_name_filter=get_case_study_file_name_filter(case_study)
            )
            perf_inter_reports = {
                report_file.report_filename.commit_hash:
                load_performance_interaction_report(report_file)
                for report_file in perf_inter_report_files
            }

            threshold_data: tp.Dict[
                float,
                ConfusionMatrixData] = defaultdict(lambda: defaultdict(list))
            predicted = 0

            for old_rev, new_rev in pairwise(revisions):
                old_rev_short = old_rev.to_short_commit_hash()
                new_rev_short = new_rev.to_short_commit_hash()
                report = perf_inter_reports.get(
                    new_rev.to_short_commit_hash(), None
                )
                if (
                    old_rev_short not in performance_data.columns or
                    new_rev_short not in performance_data.columns
                ):
                    continue

                if report is not None and report.performance_interactions:
                    predicted += 1

                for threshold in thresholds:
                    current_data = threshold_data[threshold]

                    is_reg, _ = is_regression(
                        performance_data, old_rev_short, new_rev_short, configs,
                        threshold, min_diff
                    )

                    if is_reg:
                        current_data["actual_positive_values"].append(new_rev)
                    else:
                        current_data["actual_negative_values"].append(new_rev)

                    # performance interaction classification
                    if report is not None and report.performance_interactions:
                        current_data["predicted_positive_values"].append(
                            new_rev
                        )
                    else:
                        current_data["predicted_negative_values"].append(
                            new_rev
                        )

            cs_data: tp.Dict[tp.Any, tp.Any] = {
                ("Project",): [project_name],
                ("Revisions",): [len(case_study.revisions)],
                ("Predicted",): [predicted]
            }

            for threshold in thresholds:
                current_data = threshold_data[threshold]
                confusion_matrix = ConfusionMatrix(
                    current_data["actual_positive_values"],
                    current_data["actual_negative_values"],
                    current_data["predicted_positive_values"],
                    current_data["predicted_negative_values"],
                )

                threshold_key = f"Threshold = {threshold}"
                cs_data[(threshold_key, "Base")] = [confusion_matrix.P]
                # cs_data[(threshold_key, "Pred")] = [confusion_matrix.PP]
                cs_data[(threshold_key, "Rec.")] = [confusion_matrix.recall()]
                cs_data[(threshold_key, "Prec.")
                       ] = [confusion_matrix.precision()]

            cs_df = pd.DataFrame.from_dict(cs_data)
            cs_df.set_index("Project", inplace=True)
            data.append(cs_df)

        df = pd.concat(data).sort_index()

        style = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["hrules"] = True
            kwargs["column_format"] = "lrr" + "|rrr" * len(thresholds)
            kwargs["multicol_align"] = "c"
            style.format(precision=2, thousands=r"\,")

        return dataframe_to_table(
            df, table_format, style, wrap_table, wrap_landscape=True, **kwargs
        )


OPTIONAL_THRESHOLDS: CLIOptionTy = make_cli_option(
    "--threshold",
    type=float,
    default=[0.1, 0.08, 0.05],
    required=False,
    multiple=True,
    metavar="THRESHOLD",
    help="Only consider regressions where the performance difference is greater"
    "than the given threshold."
)

OPTIONAL_SIGMA: CLIOptionTy = make_cli_option(
    "--sigma",
    type=float,
    default=1,
    required=False,
    metavar="SIGMA",
    help="Only consider regressions that are at least SIGMA times greater than "
    "the standard deviation of the measurements."
)


class PerformanceRegressionClassification(
    TableGenerator,
    generator_name="perf-reg",
    options=[OPTIONAL_THRESHOLDS, OPTIONAL_SIGMA]
):
    """Generates a table that does a precision/recall analysis for performance
    regression detection for multiple thresholds."""

    def generate(self) -> tp.List[Table]:
        return [
            PerformanceRegressionClassificationTable(
                self.table_config, **self.table_kwargs
            )
        ]


class PerformanceFeaturesTable(Table, table_name="perf_feat"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        significance_level: float = 0.05

        case_study: CaseStudy = self.table_kwargs["case_study"]
        project_name: str = case_study.project_name
        commit_map: CommitMap = get_commit_map(project_name)

        heatmap = create_heatmap(case_study, project_name, commit_map)
        heatmap_diff = heatmap.diff(axis="columns")

        perf_inter_report_files = get_processed_revisions_files(
            project_name,
            PerformanceInteractionExperiment,
            file_name_filter=get_case_study_file_name_filter(case_study)
        )
        perf_inter_reports = {
            report_file.report_filename.commit_hash:
            load_performance_interaction_report(report_file)
            for report_file in perf_inter_report_files
        }

        configs = load_configuration_map_for_case_study(
            get_paper_config(), case_study, PlainCommandlineConfiguration
        )
        config_flags = []
        for id, config in configs.id_config_tuples():
            for flag in config.options():
                config_flags.append({"id": id, "flag": flag.name})
        df = pd.DataFrame(config_flags)
        feature_matrix = pd.crosstab(df["id"], df["flag"])

        data: tp.List[pd.DataFrame] = []

        for commit in heatmap_diff.columns:
            values = heatmap_diff[commit].fillna(0)
            relevant_features = rrs(feature_matrix, values, max_depth=3)
            detected_features = None
            report = perf_inter_reports.get(commit.to_short_commit_hash(), None)
            if report is not None and report.performance_interactions:
                detected_features = {
                    feature for inter in report.performance_interactions
                    for feature in inter.involved_features
                }

            data.append(
                pd.DataFrame.from_dict({
                    commit: {
                        "Base Features": str(relevant_features),
                        "Detected Featuers": str(detected_features)
                    }
                },
                                       orient="index")
            )

        df = pd.concat(data)

        style = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["hrules"] = True
            style.format(thousands=r"\,")

        return dataframe_to_table(df, table_format, style, wrap_table, **kwargs)


class PerformanceFeatures(
    TableGenerator, generator_name="perf-feat", options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List[Table]:
        return [
            PerformanceFeaturesTable(self.table_config, **self.table_kwargs)
        ]
