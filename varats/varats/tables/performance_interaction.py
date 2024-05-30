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
from varats.data.reports.performance_interaction_report import (
    PerformanceInteractionReport,
)
from varats.experiments.base.time_workloads import TimeWorkloadsSynth
from varats.experiments.vara.performance_interaction import (
    PerformanceInteractionExperiment,
    PerformanceInteractionExperimentSynthetic,
)
from varats.jupyterhelper.file import (
    load_performance_interaction_report,
    load_mpr_wl_time_report_aggregate,
    load_mpr_performance_interaction_report,
)
from varats.mapping.commit_map import get_commit_map
from varats.mapping.configuration_map import ConfigurationMap
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config, get_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.cli_util import CLIOptionTy, make_cli_option
from varats.utils.config import load_configuration_map_for_case_study
from varats.utils.git_util import ShortCommitHash

LOG = logging.Logger(__name__)

Revision = tp.Union[ShortCommitHash, str]


class Feature:

    def __init__(self, name: str, flag: str, default_value: tp.Optional[str]):
        self.name = name
        self.flag = flag
        self.default_value = default_value


F1 = Feature("FR(F1)", "f1", None)
F2 = Feature("FR(F2)", "f2", None)
F3 = Feature("FR(F3)", "f3", None)
F4 = Feature("FR(F4)", "f4", None)
F5 = Feature("FR(F5)", "f5", None)
F6 = Feature("FR(F6)", "f6", None)
F7 = Feature("FR(F7)", "f7", None)
F8 = Feature("FR(F8)", "f8", None)
F9 = Feature("FR(F9)", "f9", None)
F10 = Feature("FR(F10)", "f10", None)

CONFIG_DATA = {
    "InterStructural": [F1],
    "InterDataFlow": [F1],
    "InterImplicitFlow": [F1],
    "FunctionSingle": [F1, F2, F3],
    "FunctionAccumulating": [F1, F2, F3],
    "FunctionMultiple": [F1, F2, F3],
    "DegreeLow": [F1, F2, F3, F4, F5, F6, F7, F8, F9, F10],
    "DegreeHigh": [F1, F2, F3, F4, F5, F6, F7, F8, F9, F10],
}


class EvalData(tp.TypedDict):
    """Dict representing data for a confusion matrix."""
    baseline_positives: tp.List[Revision]
    baseline_negatives: tp.List[Revision]
    rq1_predicted_positives: tp.List[Revision]
    rq1_predicted_negatives: tp.List[Revision]
    rq2_predicted_positives: tp.List[Revision]
    rq2_predicted_negatives: tp.List[Revision]


def get_performance_data(
    performance_data: pd.DataFrame, revision: Revision, config_id: int
) -> tp.List[float]:
    vals_raw = performance_data.loc[config_id, revision]

    if isinstance(vals_raw, str):
        return ast.literal_eval(vals_raw)
    return vals_raw


def is_regression(
    performance_data: pd.DataFrame, old_rev: Revision, new_rev: Revision,
    configs: ConfigurationMap, threshold: float, sigma: float
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
        sigma: factor that controls the minimum difference to the standard
                  deviation of the measurements

    Returns:
    """
    num_regressions = 0
    for cid in configs.ids():
        old_vals = get_performance_data(performance_data, old_rev, cid)
        new_vals = get_performance_data(performance_data, new_rev, cid)

        std_old = np.std(old_vals)
        std_new = np.std(new_vals)
        std = max(std_old, std_new)

        old_avg = np.average(old_vals)
        new_avg = np.average(new_vals)
        diff = abs(old_avg - new_avg)

        if diff >= max(threshold * old_avg, sigma * std):
            num_regressions += 1

    return num_regressions > 0, num_regressions


def get_relevant_configs(
    project_name: str, configs: ConfigurationMap,
    perf_inter_report: PerformanceInteractionReport
) -> ConfigurationMap:
    """
    Computes relevant configurations according to a performance interaction
    report.

    We include all configurations where only relevant features vary and all
    other features are set to their default value.
    """
    relevant_features = set()
    for inter in perf_inter_report.performance_interactions:
        relevant_features.update(inter.involved_features)
    relevant_configs: ConfigurationMap = ConfigurationMap()
    default_features = [
        feature for feature in CONFIG_DATA[project_name]
        if feature.name not in relevant_features
    ]
    # collect all configs where the default features are set to their default value
    for config in configs.configurations():
        is_relevant_config = True
        for feature in default_features:
            if config.get_config_value(feature.flag) != feature.default_value:
                is_relevant_config = False
                break

        if is_relevant_config:
            relevant_configs.add_configuration(config)
    return relevant_configs


def calculate_eval_data(
    project_name: str, performance_data: pd.DataFrame, old_rev: Revision,
    new_rev: Revision, configs: ConfigurationMap,
    report: PerformanceInteractionReport, threshold: float, sigma: int,
    eval_data: EvalData
) -> None:
    # RQ1
    is_reg, _ = is_regression(
        performance_data, old_rev, new_rev, configs, threshold, sigma
    )

    if is_reg:
        eval_data["baseline_positives"].append(new_rev)
    else:
        eval_data["baseline_negatives"].append(new_rev)

    # performance interaction classification
    if report is not None and report.performance_interactions:
        eval_data["rq1_predicted_positives"].append(new_rev)
    else:
        eval_data["rq1_predicted_negatives"].append(new_rev)

    # RQ2
    if report is not None and is_reg:
        relevant_configs = get_relevant_configs(project_name, configs, report)

        is_reg2, _ = is_regression(
            performance_data, old_rev, new_rev, relevant_configs, threshold,
            sigma
        )

        if is_reg2:
            eval_data["rq2_predicted_positives"].append(new_rev)
        else:
            eval_data["rq2_predicted_negatives"].append(new_rev)


def calculate_case_study_data(
    project_name: str, performance_data: pd.DataFrame, revision_pairs,
    configs: ConfigurationMap,
    perf_inter_reports: tp.Dict[Revision, PerformanceInteractionReport],
    threshold: float, sigma: int
) -> pd.DataFrame:
    eval_data: EvalData = defaultdict(list)

    for old_rev, new_rev in revision_pairs:
        if (
            old_rev not in performance_data.columns or
            new_rev not in performance_data.columns
        ):
            continue

        report = perf_inter_reports.get(new_rev, None)
        calculate_eval_data(
            project_name, performance_data, old_rev, new_rev, configs, report,
            threshold, sigma, eval_data
        )

    confusion_matrix = ConfusionMatrix(
        eval_data["baseline_positives"],
        eval_data["baseline_negatives"],
        eval_data["rq1_predicted_positives"],
        eval_data["rq1_predicted_negatives"],
    )

    rq2_confusion_matrix = ConfusionMatrix(
        eval_data["baseline_positives"],
        eval_data["baseline_negatives"],
        eval_data["rq2_predicted_positives"],
        eval_data["rq2_predicted_negatives"],
    )

    threshold_key = f"Threshold = {threshold}"
    cs_data: tp.Dict[tp.Any, tp.Any] = {
        ("Project",): [project_name],
        (threshold_key, "Base"): [confusion_matrix.P],
        (threshold_key, "RQ1 Pred."): [confusion_matrix.PP],
        (threshold_key, "RQ1 Rec."): [confusion_matrix.recall()],
        (threshold_key, "RQ1 Prec."): [confusion_matrix.precision()],
        (threshold_key, "RQ2 Pred."): [rq2_confusion_matrix.PP],
        (threshold_key, "RQ2 bACC"): [rq2_confusion_matrix.balanced_accuracy()]
    }

    cs_df = pd.DataFrame.from_dict(cs_data)
    cs_df.set_index("Project", inplace=True)
    return cs_df


def calculate_saved_costs(
    project_name: str, revision: Revision, configs: ConfigurationMap,
    perf_inter_report: PerformanceInteractionReport,
    performance_data: pd.DataFrame
) -> tp.Tuple[float, float, float]:
    # RQ3
    relevant_configs = get_relevant_configs(
        project_name, configs, perf_inter_report
    )
    t_baseline = 0
    t_rq3 = 0

    for config_id in configs.ids():
        new_vals = get_performance_data(performance_data, revision, config_id)
        t_baseline += np.average(new_vals)

    for config_id in relevant_configs.ids():
        new_vals = get_performance_data(performance_data, revision, config_id)
        t_rq3 += np.average(new_vals)

    absolute_savings = len(configs.ids()) - len(relevant_configs.ids())
    relative_savings = 1 - len(relevant_configs.ids()) / len(configs.ids())
    time_savings = t_baseline - t_rq3

    return absolute_savings, relative_savings, time_savings


class PerformanceRegressionClassificationTable(Table, table_name="perf_reg"):
    """Table for performance regression classification analysis."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        threshold = self.table_kwargs["threshold"]  # % diff
        sigma = self.table_kwargs["sigma"]  # times std

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
            revision_pairs = pairwise([
                rev.to_short_commit_hash() for rev in revisions
            ])

            data.append(
                calculate_case_study_data(
                    project_name, performance_data, revision_pairs, configs,
                    perf_inter_reports, threshold, sigma
                )
            )

        df = pd.concat(data).sort_index()

        style = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["hrules"] = True
            kwargs["column_format"] = "lr|rrr|rr"
            kwargs["multicol_align"] = "c"
            style.format(precision=2, thousands=r"\,")

        return dataframe_to_table(
            df, table_format, style, wrap_table, wrap_landscape=True, **kwargs
        )


OPTIONAL_THRESHOLD: CLIOptionTy = make_cli_option(
    "--threshold",
    type=float,
    default=0.1,
    required=False,
    metavar="THRESHOLD",
    help="Only consider regressions where the performance difference is greater"
    "than the given threshold."
)

OPTIONAL_SIGMA: CLIOptionTy = make_cli_option(
    "--sigma",
    type=float,
    default=3,
    required=False,
    metavar="SIGMA",
    help="Only consider regressions that are at least SIGMA times greater than "
    "the standard deviation of the measurements."
)


class PerformanceRegressionClassification(
    TableGenerator,
    generator_name="perf-reg",
    options=[OPTIONAL_THRESHOLD, OPTIONAL_SIGMA]
):
    """Generates a table that does a precision/recall analysis for performance
    regression detection for multiple thresholds."""

    def generate(self) -> tp.List[Table]:
        return [
            PerformanceRegressionClassificationTable(
                self.table_config, **self.table_kwargs
            )
        ]


def load_synth_baseline_data(
    case_study: CaseStudy, config_ids: tp.List[int]
) -> pd.DataFrame:
    project_name = case_study.project_name

    data: tp.List[tp.Dict[str, tp.Any]] = []

    for config_id in config_ids:
        time_report_files = get_processed_revisions_files(
            project_name,
            TimeWorkloadsSynth,
            file_name_filter=get_case_study_file_name_filter(case_study),
            only_newest=True,
            config_id=config_id
        )

        if not time_report_files:
            LOG.warning(
                f"No baseline report found for {project_name}:{config_id}, skipping."
            )
            continue

        assert len(time_report_files) == 1
        time_report = load_mpr_wl_time_report_aggregate(time_report_files[0])

        baseline_report = time_report.get_baseline_report()
        assert len(baseline_report.workload_names()) == 1
        workload = next(iter(baseline_report.workload_names()))
        data.append({
            "revision":
                "base",
            "config_id":
                config_id,
            "wall_clock_time":
                baseline_report.measurements_wall_clock_time(workload)
        })

        for patch_name in time_report.get_patch_names():
            patched_report = time_report.get_report_for_patch(patch_name)
            assert len(patched_report.workload_names()) == 1
            workload = next(iter(patched_report.workload_names()))
            data.append({
                "revision":
                    patch_name,
                "config_id":
                    config_id,
                "wall_clock_time":
                    patched_report.measurements_wall_clock_time(workload)
            })

    return pd.DataFrame.from_records(data)


def load_synth_perf_inter_reports(
    case_study: CaseStudy
) -> tp.Dict[str, PerformanceInteractionReport]:
    project_name = case_study.project_name

    report_files = get_processed_revisions_files(
        project_name,
        PerformanceInteractionExperimentSynthetic,
        file_name_filter=get_case_study_file_name_filter(case_study),
        only_newest=True
    )

    if not report_files:
        LOG.warning(
            f"No performance interaction report found for {project_name}, skipping."
        )
        return {}

    assert len(report_files) == 1
    report = load_mpr_performance_interaction_report(report_files[0])

    report_dict: tp.Dict[str:PerformanceInteractionReport] = {
        "base": report.get_baseline_report()
    }
    for patch_name in report.get_patch_names():
        report_dict[patch_name] = report.get_report_for_patch(patch_name)

    return report_dict


class PerformanceRegressionClassificationTableSynth(
    Table, table_name="perf_reg_synth"
):
    """Table for performance regression classification analysis for synthetic
    case studies."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        threshold = self.table_kwargs["threshold"]  # % diff
        sigma = self.table_kwargs["sigma"]  # times std

        case_studies = get_loaded_paper_config().get_all_case_studies()

        data: tp.List[pd.DataFrame] = []
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
            revision_pairs = [("base", patch_name) for patch_name in revisions]

            data.append(
                calculate_case_study_data(
                    project_name, performance_data, revision_pairs, configs,
                    perf_inter_reports, threshold, sigma
                )
            )

        df = pd.concat(data).sort_index()

        style = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["hrules"] = True
            kwargs["column_format"] = "lr|rrr|rr"
            kwargs["multicol_align"] = "c"
            style.format(precision=2, thousands=r"\,")

        return dataframe_to_table(
            df, table_format, style, wrap_table, wrap_landscape=True, **kwargs
        )


class PerformanceRegressionClassificationSynth(
    TableGenerator,
    generator_name="perf-reg-synth",
    options=[OPTIONAL_THRESHOLD, OPTIONAL_SIGMA]
):
    """Generates a table that does a precision/recall analysis for performance
    regression detection for multiple thresholds."""

    def generate(self) -> tp.List[Table]:
        return [
            PerformanceRegressionClassificationTableSynth(
                self.table_config, **self.table_kwargs
            )
        ]
