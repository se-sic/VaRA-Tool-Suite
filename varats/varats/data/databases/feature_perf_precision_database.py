"""Shared data aggregation function for analyzing feature performance."""
import abc
import typing as tp
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy.stats import ttest_ind

import varats.experiments.vara.feature_perf_precision as fpp
from varats.data.metrics import ClassificationResults
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.gnu_time_report import TimeReportAggregate
from varats.report.report import BaseReport, ReportFilepath
from varats.report.tef_report import (
    TEFReport,
    TraceEvent,
    TraceEventType,
    TEFReportAggregate,
)
from varats.revision.revisions import get_processed_revisions_files
from varats.utils.git_util import FullCommitHash


def get_interactions_from_fr_string(interactions: str) -> str:
    """Convert the feature strings in a TEFReport from FR(x,y) to x*y, similar
    to the format used by SPLConqueror."""
    interactions = (
        interactions.replace("FR", "").replace("(", "").replace(")", "")
    )
    interactions_list = interactions.split(",")
    # Ignore interactions with base, but do not remove base if it's the only
    # feature
    if "Base" in interactions_list and len(interactions_list) > 1:
        interactions_list.remove("Base")
    # Features cannot interact with itself, so remove duplicastes
    interactions_list = list(set(interactions_list))

    interactions_str = "*".join(interactions_list)

    return interactions_str


def get_feature_performance_from_tef_report(
    tef_report: TEFReport,
) -> tp.Dict[str, int]:
    """Extract feature performance from a TEFReport."""
    open_events: tp.List[TraceEvent] = []

    feature_performances: tp.Dict[str, int] = {}

    for trace_event in tef_report.trace_events:
        if trace_event.category == "Feature":
            if (trace_event.event_type == TraceEventType.DURATION_EVENT_BEGIN):
                open_events.append(trace_event)
            elif (trace_event.event_type == TraceEventType.DURATION_EVENT_END):
                opening_event = open_events.pop()

                end_timestamp = trace_event.timestamp
                begin_timestamp = opening_event.timestamp

                # Subtract feature duration from parent duration such that
                # it is not counted twice, similar to behavior in
                # Performance-Influence models.
                interactions = [event.name for event in open_events]
                if open_events:
                    # Parent is equivalent to interaction of all open
                    # events.
                    interaction_string = get_interactions_from_fr_string(
                        ",".join(interactions)
                    )
                    if interaction_string in feature_performances:
                        feature_performances[interaction_string] -= (
                            end_timestamp - begin_timestamp
                        )
                    else:
                        feature_performances[interaction_string] = -(
                            end_timestamp - begin_timestamp
                        )

                interaction_string = get_interactions_from_fr_string(
                    ",".join(interactions + [trace_event.name])
                )

                current_performance = feature_performances.get(
                    interaction_string, 0
                )
                feature_performances[interaction_string] = (
                    current_performance + end_timestamp - begin_timestamp
                )

    return feature_performances


class Profiler():
    """Profiler interface to add different profilers to the evaluation."""

    def __init__(
        self, name: str, experiment: tp.Type[FeatureExperiment],
        overhead_experiment: tp.Type[FeatureExperiment],
        report_type: tp.Type[BaseReport]
    ) -> None:
        self.__name = name
        self.__experiment = experiment
        self.__overhead_experiment = overhead_experiment
        self.__report_type = report_type

    @property
    def name(self) -> str:
        """Hame of the profiler used."""
        return self.__name

    @property
    def experiment(self) -> tp.Type[FeatureExperiment]:
        """Experiment used to produce this profilers information."""
        return self.__experiment

    @property
    def overhead_experiment(self) -> tp.Type[FeatureExperiment]:
        """Experiment used to produce this profilers information."""
        return self.__overhead_experiment

    @property
    def report_type(self) -> tp.Type[BaseReport]:
        """Report type used to load this profilers information."""
        return self.__report_type

    @abc.abstractmethod
    def is_regression(
        self, report_path: ReportFilepath, patch_name: str
    ) -> bool:
        """Checks if there was a regression between the old an new data."""


class VXray(Profiler):
    """Profiler mapper implementation for the vara tef tracer."""

    def __init__(self) -> None:
        super().__init__(
            "WXray", fpp.TEFProfileRunner, fpp.TEFProfileOverheadRunner,
            fpp.MPRTEFA
        )

    def is_regression(
        self, report_path: ReportFilepath, patch_name: str
    ) -> bool:
        """Checks if there was a regression between the old an new data."""
        is_regression = False

        multi_report = fpp.MultiPatchReport(
            report_path.full_path(), TEFReportAggregate
        )

        old_acc_pim: tp.DefaultDict[str, tp.List[int]] = defaultdict(list)
        for old_tef_report in multi_report.get_baseline_report().reports():
            pim = get_feature_performance_from_tef_report(old_tef_report)
            for feature, value in pim.items():
                old_acc_pim[feature].append(value)

        new_acc_pim: tp.DefaultDict[str, tp.List[int]] = defaultdict(list)
        opt_mr = multi_report.get_report_for_patch(patch_name)
        if not opt_mr:
            raise NotImplementedError()

        for new_tef_report in opt_mr.reports():
            pim = get_feature_performance_from_tef_report(new_tef_report)
            for feature, value in pim.items():
                new_acc_pim[feature].append(value)

        for feature, old_values in old_acc_pim.items():
            if feature in new_acc_pim:
                new_values = new_acc_pim[feature]
                ttest_res = ttest_ind(old_values, new_values)

                # TODO: check, maybe we need a "very small value cut off"
                if ttest_res.pvalue < 0.05:
                    # print(
                    #     f"{self.name} found regression for feature {feature}."
                    # )
                    is_regression = True
            else:
                print(f"Could not find feature {feature} in new trace.")
                # TODO: how to handle this?
                is_regression = True

        return is_regression


class PIMTracer(Profiler):
    """Profiler mapper implementation for the vara performance-influence-model
    tracer."""

    def __init__(self) -> None:
        super().__init__(
            "PIMTracer", fpp.PIMProfileRunner, fpp.PIMProfileOverheadRunner,
            fpp.MPRPIMA
        )

    def is_regression(
        self, report_path: ReportFilepath, patch_name: str
    ) -> bool:
        """Checks if there was a regression between the old an new data."""
        is_regression = False

        multi_report = fpp.MultiPatchReport(
            report_path.full_path(), fpp.PerfInfluenceTraceReportAggregate
        )

        old_acc_pim: tp.DefaultDict[str, tp.List[int]] = defaultdict(list)
        for old_pim_report in multi_report.get_baseline_report().reports():
            for region_inter in old_pim_report.region_interaction_entries:
                name = get_interactions_from_fr_string(
                    old_pim_report._translate_interaction(
                        region_inter.interaction
                    )
                )
                time = region_inter.time
                old_acc_pim[name].append(time)

        new_acc_pim: tp.DefaultDict[str, tp.List[int]] = defaultdict(list)
        opt_mr = multi_report.get_report_for_patch(patch_name)
        if not opt_mr:
            raise NotImplementedError()

        for new_pim_report in opt_mr.reports():
            for region_inter in new_pim_report.region_interaction_entries:
                name = get_interactions_from_fr_string(
                    new_pim_report._translate_interaction(
                        region_inter.interaction
                    )
                )
                time = region_inter.time
                new_acc_pim[name].append(time)

        # TODO: same for TEF
        for feature, old_values in old_acc_pim.items():
            if feature in new_acc_pim:
                new_values = new_acc_pim[feature]
                ttest_res = ttest_ind(old_values, new_values)

                # TODO: check, maybe we need a "very small value cut off"
                if ttest_res.pvalue < 0.05:
                    # print(
                    #     f"{self.name} found regression for feature {feature}."
                    # )
                    is_regression = True
            else:
                print(f"Could not find feature {feature} in new trace.")
                # TODO: how to handle this?
                is_regression = True

        return is_regression


def get_patch_names(case_study: CaseStudy) -> tp.List[str]:
    report_files = get_processed_revisions_files(
        case_study.project_name,
        fpp.BlackBoxBaselineRunner,
        fpp.MPRTRA,
        get_case_study_file_name_filter(case_study),
        config_id=0
    )

    if len(report_files) > 1:
        raise AssertionError("Should only be one")
    if not report_files:
        print(
            f"Could not find profiling data for {case_study.project_name}"
            ". config_id=0, profiler=Baseline"
        )
        return []

    # TODO: fix to prevent double loading
    time_reports = fpp.MPRTRA(report_files[0].full_path())
    return time_reports.get_patch_names()


def get_regressing_config_ids_gt(
    project_name: str, case_study: CaseStudy, rev: FullCommitHash,
    report_name: str
) -> tp.Optional[tp.Dict[int, bool]]:
    """Computes the baseline data, i.e., the config ids where a regression was
    identified."""

    gt: tp.Dict[int, bool] = {}

    for config_id in case_study.get_config_ids_for_revision(rev):
        report_files = get_processed_revisions_files(
            project_name,
            fpp.BlackBoxBaselineRunner,
            fpp.MPRTRA,
            get_case_study_file_name_filter(case_study),
            config_id=config_id
        )
        if len(report_files) > 1:
            raise AssertionError("Should only be one")
        if not report_files:
            print(
                f"Could not find profiling data for {case_study.project_name}."
                f" {config_id=}, profiler=Baseline"
            )
            return None

        # TODO: fix to prevent double loading
        time_reports = fpp.MPRTRA(report_files[0].full_path())

        old_time = time_reports.get_baseline_report()
        # new_time = time_reports.get_new_report()
        new_time = time_reports.get_report_for_patch(report_name)
        if not new_time:
            return None

        if np.mean(old_time.measurements_wall_clock_time
                  ) == np.mean(new_time.measurements_wall_clock_time):
            gt[config_id] = False
        else:
            # TODO: double check ttest handling
            ttest_res = ttest_ind(
                old_time.measurements_wall_clock_time,
                new_time.measurements_wall_clock_time
            )
            if ttest_res.pvalue < 0.05:
                gt[config_id] = True
            else:
                gt[config_id] = False

    return gt


def map_to_positive_config_ids(reg_dict: tp.Dict[int, bool]) -> tp.List[int]:
    return [config_id for config_id, value in reg_dict.items() if value is True]


def map_to_negative_config_ids(reg_dict: tp.Dict[int, bool]) -> tp.List[int]:
    return [
        config_id for config_id, value in reg_dict.items() if value is False
    ]


class Baseline(Profiler):
    """Profiler mapper implementation for the black-box baseline."""

    def __init__(self) -> None:
        super().__init__(
            "Base", fpp.BlackBoxBaselineRunner, fpp.BlackBoxOverheadBaseline,
            fpp.TimeReportAggregate
        )

    def is_regression(self, report_path: ReportFilepath) -> bool:
        raise NotImplementedError()


def compute_profiler_predictions(
    profiler: Profiler, project_name: str, case_study: CaseStudy,
    config_ids: tp.List[int], patch_name: str
) -> tp.Optional[tp.Dict[int, bool]]:
    """Computes the regression predictions for a given profiler."""

    result_dict: tp.Dict[int, bool] = {}
    for config_id in config_ids:
        report_files = get_processed_revisions_files(
            project_name,
            profiler.experiment,
            profiler.report_type,
            get_case_study_file_name_filter(case_study),
            config_id=config_id
        )

        if len(report_files) > 1:
            raise AssertionError("Should only be one")
        if not report_files:
            print(
                f"Could not find profiling data. {config_id=}, "
                f"profiler={profiler.name}"
            )
            return None

        result_dict[config_id] = profiler.is_regression(
            report_files[0], patch_name
        )

    return result_dict


class OverheadData:

    def __init__(
        self, profiler, mean_time: tp.Dict[int, float],
        ctx_switches: tp.Dict[int, float]
    ) -> None:
        self.__profiler = profiler
        self.__mean_time: tp.Dict[int, float] = mean_time
        self.__mean_ctx_switches: tp.Dict[int, float] = ctx_switches

    def mean_time(self) -> float:
        return float(np.mean(list(self.__mean_time.values())))

    def mean_ctx(self) -> float:
        return float(np.mean(list(self.__mean_ctx_switches.values())))

    def config_wise_time_diff(self,
                              other: 'OverheadData') -> tp.Dict[int, float]:
        return self.__config_wise(self.__mean_time, other.__mean_time)

    def config_wise_ctx_diff(self,
                             other: 'OverheadData') -> tp.Dict[int, float]:
        return self.__config_wise(
            self.__mean_ctx_switches, other.__mean_ctx_switches
        )

    @staticmethod
    def __config_wise(
        self_map: tp.Dict[int, float], other_map: tp.Dict[int, float]
    ) -> tp.Dict[int, float]:
        gen_diff: tp.Dict[int, float] = {}
        for config_id, gen_value in self_map.items():
            if config_id not in other_map:
                raise AssertionError("Could not find config id in other")

            gen_diff[config_id] = gen_value - other_map[config_id]

        return gen_diff

    @staticmethod
    def compute_overhead_data(
        profiler: Profiler, case_study: CaseStudy, rev: FullCommitHash
    ) -> tp.Optional['OverheadData']:

        mean_time: tp.Dict[int, float] = {}
        mean_cxt_switches: tp.Dict[int, float] = {}

        for config_id in case_study.get_config_ids_for_revision(rev):
            report_files = get_processed_revisions_files(
                case_study.project_name,
                profiler.overhead_experiment,
                TimeReportAggregate,
                get_case_study_file_name_filter(case_study),
                config_id=config_id
            )

            if len(report_files) > 1:
                raise AssertionError("Should only be one")
            if not report_files:
                print(
                    f"Could not find overhead data. {config_id=}, "
                    f"profiler={profiler.name}"
                )
                return None

            time_report = TimeReportAggregate(report_files[0].full_path())
            mean_time[config_id] = float(
                np.mean(time_report.measurements_wall_clock_time)
            )
            mean_cxt_switches[config_id] = float(
                np.mean(time_report.measurements_ctx_switches)
            )
        if not mean_time:
            print(
                f"Case study for project {case_study.project_name} had "
                "no configs, skipping..."
            )
            return None

        # print(f"{mean_time=}")
        return OverheadData(profiler, mean_time, mean_cxt_switches)


def load_precision_data(case_studies, profilers) -> pd.DataFrame:
    table_rows_plot = []
    for case_study in case_studies:
        for patch_name in get_patch_names(case_study):
            rev = case_study.revisions[0]
            project_name = case_study.project_name

            ground_truth = get_regressing_config_ids_gt(
                project_name, case_study, rev, patch_name
            )

            for profiler in profilers:
                new_row = {
                    'CaseStudy':
                        project_name,
                    'Patch':
                        patch_name,
                    'Configs':
                        len(case_study.get_config_ids_for_revision(rev)),
                    'RegressedConfigs':
                        len(map_to_positive_config_ids(ground_truth))
                        if ground_truth else -1
                }

                # TODO: multiple patch cycles
                predicted = compute_profiler_predictions(
                    profiler, project_name, case_study,
                    case_study.get_config_ids_for_revision(rev), patch_name
                )

                if ground_truth and predicted:
                    results = ClassificationResults(
                        map_to_positive_config_ids(ground_truth),
                        map_to_negative_config_ids(ground_truth),
                        map_to_positive_config_ids(predicted),
                        map_to_negative_config_ids(predicted)
                    )

                    new_row['precision'] = results.precision()
                    new_row['recall'] = results.recall()
                    new_row['f1_score'] = results.f1_score()
                    new_row['Profiler'] = profiler.name
                    # new_row[f"{profiler.name}_precision"
                    #        ] = results.precision()
                    # new_row[f"{profiler.name}_recall"] = results.recall()
                    # new_row[f"{profiler.name}_baccuracy"
                    #        ] = results.balanced_accuracy()
                else:
                    new_row['precision'] = np.nan
                    new_row['recall'] = np.nan
                    new_row['f1_score'] = np.nan
                    new_row['Profiler'] = profiler.name

                table_rows_plot.append(new_row)

    return pd.DataFrame(table_rows_plot)


def load_overhead_data(case_studies, profilers) -> pd.DataFrame:
    table_rows = []

    for case_study in case_studies:
        rev = case_study.revisions[0]
        project_name = case_study.project_name

        overhead_ground_truth = OverheadData.compute_overhead_data(
            Baseline(), case_study, rev
        )
        if not overhead_ground_truth:
            print(f"No baseline data for {case_study.project_name}, skipping")
            continue

        new_row = {
            'CaseStudy': project_name,
            'Profiler': "Base",
            'time':
                overhead_ground_truth.mean_time(),  # random.randint(2, 230),
            'ctx': overhead_ground_truth.mean_ctx(),
            'overhead_time': 0,
            'overhead_ctx': 0
        }

        table_rows.append(new_row)

        for profiler in profilers:
            profiler_overhead = OverheadData.compute_overhead_data(
                profiler, case_study, rev
            )

            new_row = {'CaseStudy': project_name, 'Profiler': profiler.name}

            if profiler_overhead:
                time_diff = profiler_overhead.config_wise_time_diff(
                    overhead_ground_truth
                )
                ctx_diff = profiler_overhead.config_wise_ctx_diff(
                    overhead_ground_truth
                )

                new_row['time'] = profiler_overhead.mean_time()
                new_row['overhead_time'] = np.mean(list(time_diff.values()))

                new_row['ctx'] = profiler_overhead.mean_ctx()
                new_row['overhead_ctx'] = np.mean(list(ctx_diff.values()))
            else:
                new_row['time'] = np.nan
                new_row['overhead_time'] = np.nan

                new_row['ctx'] = np.nan
                new_row['overhead_ctx'] = np.nan

            table_rows.append(new_row)

    return pd.DataFrame(table_rows)
