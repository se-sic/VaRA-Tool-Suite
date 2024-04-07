"""Performance interaction eval."""
import ast
import logging
import typing as tp
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
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config, get_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.plots.performance_evolution import create_heatmap, rrs
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.click_param_types import REQUIRE_CASE_STUDY
from varats.utils.config import load_configuration_map_for_case_study
from varats.utils.git_util import FullCommitHash

LOG = logging.Logger(__name__)


class PerformanceRegressionClassificationTable(Table, table_name="perf_reg"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        data: tp.List[pd.DataFrame] = []
        for case_study in case_studies:
            project_name = case_study.project_name
            commit_map = get_commit_map(project_name)

            revisions = sorted(case_study.revisions, key=commit_map.time_id)

            configs = load_configuration_map_for_case_study(
                get_paper_config(), case_study, PlainCommandlineConfiguration
            )

            performance_data = PerformanceEvolutionDatabase.get_data_for_project(
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

            actual_positive_values: tp.List[FullCommitHash] = []
            actual_negative_values: tp.List[FullCommitHash] = []
            predicted_positive_values: tp.List[FullCommitHash] = []
            predicted_negative_values: tp.List[FullCommitHash] = []

            for old_rev, new_rev in pairwise(revisions):
                old_rev_short = old_rev.to_short_commit_hash()
                new_rev_short = new_rev.to_short_commit_hash()
                report = perf_inter_reports.get(
                    new_rev.to_short_commit_hash(), None
                )
                if old_rev_short not in performance_data.columns or new_rev_short not in performance_data.columns:
                    continue

                # ground truth classification
                is_regression = False
                num_regressions = 0
                for cid in configs.ids():
                    old_vals = ast.literal_eval(
                        performance_data.loc[cid, old_rev_short]
                    )
                    new_vals = ast.literal_eval(
                        performance_data.loc[cid, new_rev_short]
                    )

                    old_vals += old_vals
                    old_vals += old_vals
                    new_vals += new_vals
                    new_vals += new_vals

                    threshold = 0.05
                    old_avg = np.average(old_vals)
                    new_avg = np.average(new_vals)
                    diff = abs(old_avg - new_avg)
                    percent_change = diff / old_avg

                    if percent_change > threshold:
                        # if diff > threshold:
                        is_regression = True
                        num_regressions += 1

                    # _, p = mannwhitneyu(old_vals, new_vals)
                    # if p < significance_level:
                    #     is_regression = True
                    #     num_regressions += 1
                    #     # break

                print(f"{new_rev}: {num_regressions} regressing configs found.")
                if is_regression:
                    actual_positive_values.append(new_rev)
                else:
                    # print(f"{new_rev}: No regressing configs found.")
                    actual_negative_values.append(new_rev)

                # performance interaction classification
                if report is not None and report.performance_interactions:
                    predicted_positive_values.append(new_rev)
                else:
                    predicted_negative_values.append(new_rev)

            confusion_matrix = ConfusionMatrix(
                actual_positive_values,
                actual_negative_values,
                predicted_positive_values,
                predicted_negative_values,
            )
            cs_data = {
                project_name: {
                    "Revisions": confusion_matrix.P + confusion_matrix.N,
                    "Regressions": confusion_matrix.P,
                    "Detected": confusion_matrix.PP,
                    "Recall": confusion_matrix.recall(),
                    "Precision": confusion_matrix.precision(),
                }
            }

            data.append(pd.DataFrame.from_dict(cs_data, orient="index"))

        df = pd.concat(data).sort_index()

        style = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["hrules"] = True
            style.format(thousands=r"\,")

        return dataframe_to_table(df, table_format, style, wrap_table, **kwargs)


class PerformanceRegressionClassification(
    TableGenerator, generator_name="perf-reg", options=[]
):

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
