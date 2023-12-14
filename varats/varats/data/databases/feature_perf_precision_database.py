"""Shared data aggregation function for analyzing feature performance."""
import abc
import json
import logging
import traceback
import typing as tp
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from benchbuild.utils.cmd import mkdir
from cliffs_delta import cliffs_delta  # type: ignore
from scipy.stats import ttest_ind

import varats.experiments.vara.feature_perf_precision as fpp
from varats.data.metrics import ConfusionMatrix
from varats.data.reports.performance_influence_trace_report import (
    PerfInfluenceTraceReport,
    PerfInfluenceTraceReportAggregate,
)
from varats.data.reports.tef_feature_identifier_report import (
    TEFFeatureIdentifierReport,
)
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.experiments.vara.tef_region_identifier import TEFFeatureIdentifier
from varats.jupyterhelper.file import load_mpr_time_report_aggregate
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.gnu_time_report import TimeReportAggregate
from varats.report.multi_patch_report import MultiPatchReport
from varats.report.report import BaseReport, ReportFilepath
from varats.report.tef_report import (
    TEFReport,
    TraceEvent,
    TraceEventType,
    TEFReportAggregate,
)
from varats.revision.revisions import get_processed_revisions_files
from varats.utils.git_util import FullCommitHash
from varats.utils.settings import bb_cfg

LOG = logging.getLogger(__name__)


def get_interactions_from_fr_string(interactions: str, sep: str = ",") -> str:
    """Convert the feature strings in a TEFReport from FR(x,y) to x*y, similar
    to the format used by SPLConqueror."""
    interactions = (
        interactions.replace("FR", "").replace("(", "").replace(")", "")
    )
    interactions_list = interactions.split(sep)

    # Features cannot interact with itself, so remove duplicates
    interactions_list = list(set(interactions_list))

    # Ignore interactions with base, but do not remove base if it's the only
    # feature
    if "Base" in interactions_list and len(interactions_list) > 1:
        interactions_list.remove("Base")

    interactions_str = "*".join(interactions_list)

    return interactions_str


def get_matching_event(
    open_events: tp.List[TraceEvent], closing_event: TraceEvent
):
    for event in open_events:
        if (
            event.uuid == closing_event.uuid and
            event.pid == closing_event.pid and event.tid == closing_event.tid
        ):
            open_events.remove(event)
            return event

    LOG.debug(f"Could not find matching start for Event {repr(closing_event)}.")

    return None


def get_feature_performance_from_tef_report(
    tef_report: TEFReport,
) -> tp.Dict[str, int]:
    """Extract feature performance from a TEFReport."""
    open_events: tp.List[TraceEvent] = []

    feature_performances: tp.Dict[str, int] = {}

    found_missing_open_event = False
    for trace_event in tef_report.trace_events:
        if trace_event.category == "Feature":
            if trace_event.event_type == TraceEventType.DURATION_EVENT_BEGIN:
                # open_events.append(trace_event)
                # insert event at the top of the list
                open_events.insert(0, trace_event)
            elif trace_event.event_type == TraceEventType.DURATION_EVENT_END:
                opening_event = get_matching_event(open_events, trace_event)
                if not opening_event:
                    found_missing_open_event = True
                    continue

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

    if open_events:
        LOG.error("Not all events have been correctly closed.")
        LOG.debug(f"Events = {open_events}.")

    if found_missing_open_event:
        LOG.error("Not all events have been correctly opened.")

    return feature_performances


def is_feature_relevant(
    old_measurements: tp.List[int],
    new_measurements: tp.List[int],
    rel_cut_off: float = 0.01,
    abs_cut_off: int = 20
) -> bool:
    """Check if a feature can be ignored for regression checking as it's time
    measurements seem not relevant."""
    old_mean = np.mean(old_measurements)
    new_mean = np.mean(new_measurements)

    if old_mean < abs_cut_off and new_mean < abs_cut_off:
        return False

    old_rel_cut_off = old_mean * rel_cut_off
    abs_mean_diff = abs(old_mean - new_mean)
    if abs_mean_diff < old_rel_cut_off:
        return False

    return True


def precise_pim_regression_check(
    baseline_pim: tp.DefaultDict[str, tp.List[int]],
    current_pim: tp.DefaultDict[str, tp.List[int]],
    rel_cut_off: float = 0.01,
    abs_cut_off: int = 20
) -> bool:
    """Compute if there was a regression in one of the feature terms of the
    model between the current and the baseline, using a Mann-Whitney U test."""
    is_regression = False

    for feature, old_values in baseline_pim.items():
        if feature in current_pim:
            if feature == "Base":
                # The regression should be identified in actual feature code
                continue

            new_values = current_pim[feature]

            # Skip features that seem not to be relevant for regressions testing
            if not is_feature_relevant(
                old_values, new_values, rel_cut_off, abs_cut_off
            ):
                continue

            ttest_res = ttest_ind(old_values, new_values)

            if ttest_res.pvalue < 0.05:
                is_regression = True
        else:
            if np.mean(old_values) > abs_cut_off:
                print(
                    f"Could not find feature {feature} in new trace. "
                    f"({np.mean(old_values)}us lost)"
                )
            # TODO: how to handle this?
            # raise NotImplementedError()
            # is_regression = True

    return is_regression


def precise_pim_feature_regression_check(
    baseline_pim: tp.DefaultDict[str, tp.List[int]],
    current_pim: tp.DefaultDict[str, tp.List[int]],
    rel_cut_off: float = 0.01,
    abs_cut_off: int = 20
) -> tp.DefaultDict[str, bool]:
    is_regression = {}

    for feature, old_values in baseline_pim.items():
        if feature in current_pim:
            if feature == "Base":
                # The regression should be identified in actual feature code
                is_regression[feature] = False
                continue

            new_values = current_pim[feature]

            # Skip features that seem not to be relevant for regressions testing
            if not is_feature_relevant(
                old_values, new_values, rel_cut_off, abs_cut_off
            ):
                is_regression[feature] = False
                continue

            ttest_res = ttest_ind(old_values, new_values)

            if ttest_res.pvalue < 0.05:
                is_regression[feature] = True
        else:
            if np.mean(old_values) > abs_cut_off:
                print(
                    f"Could not find feature {feature} in new trace. "
                    f"({np.mean(old_values)}us lost)"
                )
            # TODO: how to handle this?
            # raise NotImplementedError()
            # is_regression = True

    return is_regression


def cliffs_delta_pim_regression_check(
    baseline_pim: tp.DefaultDict[str, tp.List[int]],
    current_pim: tp.DefaultDict[str, tp.List[int]],
    rel_cut_off: float = 0.01,
    abs_cut_off: int = 20
) -> bool:
    """Compute if there was a regression in one of the feature terms of the
    model between the current and the baseline, using cliffs delta."""
    is_regression = False

    for feature, old_values in baseline_pim.items():
        if feature in current_pim:
            if feature == "Base":
                # The regression should be identified in actual feature code
                continue

            new_values = current_pim[feature]

            if not is_feature_relevant(
                old_values, new_values, rel_cut_off, abs_cut_off
            ):
                continue

            cdelta_val, _ = cliffs_delta(old_values, new_values)

            # if res == "large":
            if abs(cdelta_val) > 0.7:
                is_regression = True
        else:
            if np.mean(old_values) > abs_cut_off:
                print(
                    f"Could not find feature {feature} in new trace. "
                    f"({np.mean(old_values)}us lost)"
                )
            print(f"Could not find feature {feature} in new trace.")
            # TODO: how to handle this?
            # raise NotImplementedError()
            # is_regression = True

    return is_regression


def sum_pim_regression_check(
    baseline_pim: tp.DefaultDict[str, tp.List[int]],
    current_pim: tp.DefaultDict[str, tp.List[int]],
    rel_cut_off: float = 0.01,
    abs_cut_off: int = 20
) -> bool:
    """
    Compute if there was a regression in the sum of the features in the model
    between the current and the baseline.

    The comparison is done through a Mann-Whitney U test.
    """
    baseline_pim_totals: tp.List[tp.List[int]] = [
        old_values for feature, old_values in baseline_pim.items()
        if feature != "Base"
    ]
    current_pim_totals: tp.List[tp.List[int]] = [
        current_values for feature, current_values in current_pim.items()
        if feature != "Base"
    ]

    baseline_pim_total: tp.List[int] = [
        sum(values) for values in zip(*baseline_pim_totals)
    ]
    current_pim_total: tp.List[int] = [
        sum(values) for values in zip(*current_pim_totals)
    ]

    if not baseline_pim_total and not current_pim_total:
        # How do we get here?
        return False

    mean_baseline = np.mean(baseline_pim_total)
    mean_diff = abs(mean_baseline - np.mean(current_pim_total))
    if mean_diff < abs_cut_off or mean_diff < mean_baseline * rel_cut_off:
        return False

    u_test = ttest_ind(baseline_pim_total, current_pim_total)
    return u_test.pvalue < 0.05  # type: ignore


def pim_regression_check(
    baseline_pim: tp.DefaultDict[str, tp.List[int]],
    current_pim: tp.DefaultDict[str, tp.List[int]]
) -> bool:
    """Compares two pims and determines if there was a regression between the
    baseline and current."""
    return precise_pim_regression_check(baseline_pim, current_pim)


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

    @abc.abstractmethod
    def get_feature_regressions(
        self, report_path: ReportFilepath, patch_name: str
    ) -> tp.Dict[str, bool]:
        """Returns a list of features that regressed for a given patch."""


class VXray(Profiler):
    """Profiler mapper implementation for the vara tef tracer."""

    def __init__(
        self,
        experiment=fpp.TEFProfileRunner,
        overhead_experiment=fpp.TEFProfileOverheadRunner
    ) -> None:
        super().__init__(
            "WXray", experiment, overhead_experiment, fpp.MPRTEFAggregate
        )

    def is_regression(
        self, report_path: ReportFilepath, patch_name: str
    ) -> bool:
        """Checks if there was a regression between the old an new data."""
        multi_report = MultiPatchReport(
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

        return pim_regression_check(old_acc_pim, new_acc_pim)

    def get_feature_regressions(
        self, report_path: ReportFilepath, patch_name: str
    ):
        multi_report = MultiPatchReport(
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

        return precise_pim_feature_regression_check(old_acc_pim, new_acc_pim)


class PIMTracer(Profiler):
    """Profiler mapper implementation for the vara performance-influence-model
    tracer."""

    def get_feature_regressions(
        self, report_path: ReportFilepath, patch_name: str
    ) -> tp.Dict[str, bool]:
        multi_report = MultiPatchReport(
            report_path.full_path(), PerfInfluenceTraceReportAggregate
        )

        old_acc_pim = self.__aggregate_pim_data(
            multi_report.get_baseline_report().reports()
        )

        opt_mr = multi_report.get_report_for_patch(patch_name)
        if not opt_mr:
            raise NotImplementedError()

        new_acc_pim = self.__aggregate_pim_data(opt_mr.reports())

        return precise_pim_feature_regression_check(old_acc_pim, new_acc_pim)

    def __init__(
        self,
        experiment=fpp.PIMProfileRunner,
        overhead_experiment=fpp.PIMProfileOverheadRunner
    ) -> None:
        super().__init__(
            "PIMTracer", experiment, overhead_experiment, fpp.MPRPIMAggregate
        )

    @staticmethod
    def __aggregate_pim_data(
        reports: tp.List[PerfInfluenceTraceReport]
    ) -> tp.DefaultDict[str, tp.List[int]]:
        acc_pim: tp.DefaultDict[str, tp.List[int]] = defaultdict(list)
        for old_pim_report in reports:
            per_report_acc_pim: tp.DefaultDict[str, int] = defaultdict(int)
            for region_inter in old_pim_report.region_interaction_entries:
                name = get_interactions_from_fr_string(
                    old_pim_report._translate_interaction(
                        region_inter.interaction
                    ),
                    sep="*"
                )
                per_report_acc_pim[name] += region_inter.time

            for name, time_value in per_report_acc_pim.items():
                acc_pim[name].append(time_value)

        return acc_pim

    def is_regression(
        self, report_path: ReportFilepath, patch_name: str
    ) -> bool:
        """Checks if there was a regression between the old an new data."""
        multi_report = MultiPatchReport(
            report_path.full_path(), PerfInfluenceTraceReportAggregate
        )

        old_acc_pim = self.__aggregate_pim_data(
            multi_report.get_baseline_report().reports()
        )

        opt_mr = multi_report.get_report_for_patch(patch_name)
        if not opt_mr:
            raise NotImplementedError()

        new_acc_pim = self.__aggregate_pim_data(opt_mr.reports())

        return pim_regression_check(old_acc_pim, new_acc_pim)


class EbpfTraceTEF(Profiler):
    """Profiler mapper implementation for the vara tef tracer."""

    def __init__(
        self,
        experiment=fpp.EbpfTraceTEFProfileRunner,
        overhead_experiment=fpp.EbpfTraceTEFOverheadRunner
    ) -> None:
        super().__init__(
            "eBPFTrace", experiment, overhead_experiment, fpp.MPRTEFAggregate
        )

    def is_regression(
        self, report_path: ReportFilepath, patch_name: str
    ) -> bool:
        """Checks if there was a regression between the old an new data."""
        multi_report = MultiPatchReport(
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

        return pim_regression_check(old_acc_pim, new_acc_pim)

    def get_feature_regressions(
        self, report_path: ReportFilepath, patch_name: str
    ):
        multi_report = MultiPatchReport(
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

        return precise_pim_feature_regression_check(old_acc_pim, new_acc_pim)


def get_patch_names(case_study: CaseStudy, config_id: int) -> tp.List[str]:
    report_files = get_processed_revisions_files(
        case_study.project_name,
        fpp.BlackBoxBaselineRunner,
        fpp.MPRTimeReportAggregate,
        get_case_study_file_name_filter(case_study),
        config_id=config_id
    )

    if len(report_files) > 1:
        raise AssertionError("Should only be one")
    if not report_files:
        print(
            f"Could not find profiling data for {case_study.project_name}"
            f". config_id={config_id}, profiler=Baseline"
        )
        return []

    time_reports = load_mpr_time_report_aggregate(report_files[0].full_path())

    return time_reports.get_patch_names()


def get_regressing_config_ids_gt(
    project_name: str, case_study: CaseStudy, rev: FullCommitHash,
    patch_name: str
) -> tp.Optional[tp.Dict[int, bool]]:
    """Computes the baseline data, i.e., the config ids where a regression was
    identified."""

    ground_truth: tp.Dict[int, bool] = {}

    for config_id in case_study.get_config_ids_for_revision(rev):
        report_files = get_processed_revisions_files(
            project_name,
            fpp.BlackBoxBaselineRunner,
            fpp.MPRTimeReportAggregate,
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

        time_reports = load_mpr_time_report_aggregate(
            report_files[0].full_path()
        )

        old_time = time_reports.get_baseline_report()
        new_time = time_reports.get_report_for_patch(patch_name)
        if not new_time:
            return None

        # Cut off regressions smaller than 100ms
        req_diff = 0.1
        if np.mean(old_time.measurements_wall_clock_time
                  ) == np.mean(new_time.measurements_wall_clock_time):
            ground_truth[config_id] = False
        elif abs(
            np.mean(old_time.measurements_wall_clock_time) -
            np.mean(new_time.measurements_wall_clock_time)
        ) < req_diff:
            ground_truth[config_id] = False
        else:
            ttest_res = ttest_ind(
                old_time.measurements_wall_clock_time,
                new_time.measurements_wall_clock_time
            )

            if ttest_res.pvalue < 0.05:
                ground_truth[config_id] = True
            else:
                ground_truth[config_id] = False

    return ground_truth


def get_regressed_features_gt(
    base_reports: tp.Iterable[TEFReport],
    ground_truth_report: TEFFeatureIdentifierReport, patches: tp.Iterable[str]
) -> tp.Dict[str, bool]:
    ground_truth = {}
    for base_tef_report in base_reports:
        pim = get_feature_performance_from_tef_report(base_tef_report)
        for feature, _ in pim.items():
            ground_truth[feature] = False

    for patch_name in patches:
        detect_patch_name = patch_name[:-len("1000ms")] + "detect"
        for regions, _ in ground_truth_report.regions_for_patch(
            detect_patch_name
        ):
            if "__VARA__DETECT__" not in regions:
                continue

            actual_regions = regions - {"__VARA__DETECT__"}

            interaction_string = get_interactions_from_fr_string(
                ",".join(actual_regions)
            )

            # If this combination occurred in the ground truth experiment this means it should regress
            ground_truth[interaction_string] = True

    return ground_truth


T = tp.TypeVar('T')


def map_to_positive(reg_dict: tp.Dict[T, bool]) -> tp.List[T]:
    return [config_id for config_id, value in reg_dict.items() if value is True]


def map_to_negative(reg_dict: tp.Dict[T, bool]) -> tp.List[T]:
    return [
        config_id for config_id, value in reg_dict.items() if value is False
    ]


class Baseline(Profiler):
    """Profiler mapper implementation for the black-box baseline."""

    def __init__(self) -> None:
        super().__init__(
            "Base", fpp.BlackBoxBaselineRunner, fpp.BlackBoxOverheadBaseline,
            TimeReportAggregate
        )

    def is_regression(
        self, report_path: ReportFilepath, patch_name: str
    ) -> bool:
        multi_report = fpp.MultiPatchReport(
            report_path.full_path(), fpp.TimeReportAggregate
        )

        old_time = multi_report.get_baseline_report()
        new_time = multi_report.get_report_for_patch(patch_name)

        if not new_time:
            return False

        if np.mean(old_time.measurements_wall_clock_time
                  ) == np.mean(new_time.measurements_wall_clock_time):
            return False
        else:
            ttest_res = ttest_ind(
                old_time.measurements_wall_clock_time,
                new_time.measurements_wall_clock_time
            )

            # if res == "large":
            # if d > 0.7 or d < -0.7:
            if ttest_res.pvalue < 0.05:
                return True
            else:
                return False


def compute_profiler_predictions(
    profiler: Profiler, project_name: str, case_study: CaseStudy,
    config_ids: tp.List[int], patch_name: str
) -> tp.Optional[tp.Dict[int, bool]]:
    """Computes the regression predictions for a given profiler."""

    result_dict: tp.Dict[int, bool] = {}
    for config_id in config_ids:
        print(
            f"Compute profiler predictions:  profiler={profiler.name} - "
            f"{project_name=} - {patch_name} - {config_id=}"
        )
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
                f"Could not find profiling data for {project_name=}"
                f". {config_id=}, profiler={profiler.name}"
            )
            return None

        try:
            result_dict[config_id] = profiler.is_regression(
                report_files[0], patch_name
            )
        except Exception as exception:  # pylint: disable=W0718
            print(
                f"FAILURE: Skipping {config_id=} of {project_name=}, "
                f"profiler={profiler.name}"
            )
            print(exception)
            print(traceback.format_exc())
            # TODO: clean up
            # raise exception

    return result_dict


class OverheadData:
    """Data class to store the collected overhead data and provide high-level
    operations on it."""

    def __init__(
        self, mean_time: tp.Dict[int, float], mean_memory: tp.Dict[int, float],
        major_page_faults: tp.Dict[int,
                                   float], minor_page_faults: tp.Dict[int,
                                                                      float],
        fs_inputs: tp.Dict[int, float], fs_outputs: tp.Dict[int, float]
    ) -> None:
        self._mean_time: tp.Dict[int, float] = mean_time
        self._mean_memory: tp.Dict[int, float] = mean_memory
        self._mean_major_page_faults: tp.Dict[int, float] = major_page_faults
        self._mean_minor_page_faults: tp.Dict[int, float] = minor_page_faults
        self._mean_fs_inputs: tp.Dict[int, float] = fs_inputs
        self._mean_fs_outputs: tp.Dict[int, float] = fs_outputs

    def mean_time(self) -> float:
        return float(np.mean(list(self._mean_time.values())))

    def mean_memory(self) -> float:
        return float(np.mean(list(self._mean_memory.values())))

    def mean_major_page_faults(self) -> float:
        return float(np.mean(list(self._mean_major_page_faults.values())))

    def mean_minor_page_faults(self) -> float:
        return float(np.mean(list(self._mean_minor_page_faults.values())))

    def mean_fs_inputs(self) -> float:
        return float(np.mean(list(self._mean_fs_inputs.values())))

    def mean_fs_outputs(self) -> float:
        return float(np.mean(list(self._mean_fs_outputs.values())))

    # TODO: remove after 'Type' notation is removed
    # pylint: disable=protected-access
    def config_wise_time_diff(self,
                              other: 'OverheadData') -> tp.Dict[int, float]:
        return self.__config_wise(self._mean_time, other._mean_time)

    def config_wise_memory_diff(self,
                                other: 'OverheadData') -> tp.Dict[int, float]:
        return self.__config_wise(self._mean_memory, other._mean_memory)

    def config_wise_major_page_faults_diff(
        self, other: 'OverheadData'
    ) -> tp.Dict[int, float]:
        return self.__config_wise(
            self._mean_major_page_faults, other._mean_major_page_faults
        )

    def config_wise_minor_page_faults_diff(
        self, other: 'OverheadData'
    ) -> tp.Dict[int, float]:
        return self.__config_wise(
            self._mean_minor_page_faults, other._mean_minor_page_faults
        )

    def config_wise_fs_inputs_diff(
        self, other: 'OverheadData'
    ) -> tp.Dict[int, float]:
        return self.__config_wise(self._mean_fs_inputs, other._mean_fs_inputs)

    def config_wise_fs_outputs_diff(
        self, other: 'OverheadData'
    ) -> tp.Dict[int, float]:
        return self.__config_wise(self._mean_fs_outputs, other._mean_fs_outputs)

    # pylint: enable=protected-access

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
        """Computes overhead data for a given case study."""

        mean_time: tp.Dict[int, float] = {}
        mean_memory: tp.Dict[int, float] = {}
        mean_major_page_faults: tp.Dict[int, float] = {}
        mean_minor_page_faults: tp.Dict[int, float] = {}
        mean_fs_inputs: tp.Dict[int, float] = {}
        mean_fs_outputs: tp.Dict[int, float] = {}

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
            mean_memory[config_id] = float(
                np.mean(time_report.max_resident_sizes)
            )
            mean_major_page_faults[config_id] = float(
                np.mean(time_report.major_page_faults)
            )
            mean_minor_page_faults[config_id] = float(
                np.mean(time_report.minor_page_faults)
            )
            mean_fs_inputs[config_id] = float(
                np.mean([io[0] for io in time_report.filesystem_io])
            )
            mean_fs_outputs[config_id] = float(
                np.mean([io[1] for io in time_report.filesystem_io])
            )
        if not mean_time:
            print(
                f"Case study for project {case_study.project_name} had "
                "no configs, skipping..."
            )
            return None

        return OverheadData(
            mean_time, mean_memory, mean_major_page_faults,
            mean_minor_page_faults, mean_fs_inputs, mean_fs_outputs
        )


def load_precision_data(
    case_studies: tp.List[CaseStudy], profilers: tp.List[Profiler]
) -> pd.DataFrame:
    """Loads precision measurement data for the given cases studies and computes
    precision and recall for the different profilers."""
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
                        len(map_to_positive(ground_truth))
                        if ground_truth else -1
                }

                predicted = compute_profiler_predictions(
                    profiler, project_name, case_study,
                    case_study.get_config_ids_for_revision(rev), patch_name
                )

                if ground_truth and predicted:
                    results = ConfusionMatrix(
                        map_to_positive(ground_truth),
                        map_to_negative(ground_truth),
                        map_to_positive(predicted), map_to_negative(predicted)
                    )

                    new_row['precision'] = results.precision()
                    new_row['recall'] = results.recall()
                    new_row['f1_score'] = results.f1_score()
                    new_row['Profiler'] = profiler.name
                    new_row['fp_ids'] = results.getFPs()
                    new_row['fn_ids'] = results.getFNs()
                else:
                    new_row['precision'] = np.nan
                    new_row['recall'] = np.nan
                    new_row['f1_score'] = np.nan
                    new_row['Profiler'] = profiler.name
                    new_row['fp_ids'] = []
                    new_row['fn_ids'] = []

                table_rows_plot.append(new_row)

    return pd.DataFrame(table_rows_plot)


def _get_patches_for_patch_lists(
    project_name: str, config_id: int, profiler: Profiler
):
    result_folder_template = "{result_dir}/{project_dir}"

    vara_result_folder = result_folder_template.format(
        result_dir=str(bb_cfg()["varats"]["outfile"]), project_dir=project_name
    )

    mkdir("-p", vara_result_folder)

    json_path = Path(
        vara_result_folder
    ) / f"{config_id}-{profiler.experiment.shorthand()}.json"

    with open(json_path, "r") as f:
        p_lists = json.load(f)

    return {name: patches for name, patches in p_lists}


def load_precision_whitebox_data(
    case_studies: tp.List[CaseStudy], profilers: tp.List[Profiler]
) -> pd.DataFrame:
    table_rows = []

    for cs in case_studies:
        rev = cs.revisions[0]

        for config_id in cs.get_config_ids_for_revision(rev):
            # Load ground truth data
            ground_truth_report_files = get_processed_revisions_files(
                cs.project_name,
                TEFFeatureIdentifier,
                TEFFeatureIdentifierReport,
                get_case_study_file_name_filter(cs),
                config_id=config_id
            )

            profiler_report_files = {}

            # Load these once so we don't have to do it for every patch list
            for profiler in profilers:
                report_files = get_processed_revisions_files(
                    cs.project_name,
                    profiler.experiment,
                    profiler.report_type,
                    get_case_study_file_name_filter(cs),
                    config_id=config_id
                )

                if len(report_files) != 1:
                    print("Should only be one")
                    continue
                    # raise AssertionError("Should only be one")

                profiler_report_files[profiler] = MultiPatchReport(
                    report_files[0].full_path(), TEFReportAggregate
                )

            if len(ground_truth_report_files) != 1:
                print("Invalid number of reports from TEFIdentifier")
                continue

            ground_truth_report = TEFFeatureIdentifierReport(
                ground_truth_report_files[0].full_path()
            )

            # Load the patch lists. While we technically have different files for each profiler, the contents are
            # identical. The patch selection only depends on the configuration and project
            patch_lists = _get_patches_for_patch_lists(
                cs.project_name, config_id, profilers[0]
            )

            for list_name in patch_lists:
                # Get all patches contained in patch list
                patches = patch_lists[list_name]

                for profiler in profilers:
                    new_row = {
                        'CaseStudy': cs.project_name,
                        'PatchList': list_name,
                        'ConfigID': config_id,
                        'Profiler': profiler.name
                    }

                    if profiler not in profiler_report_files:
                        continue

                    report_file = profiler_report_files[profiler]

                    ground_truth = get_regressed_features_gt(
                        report_file.get_baseline_report().reports(),
                        ground_truth_report, patches
                    )

                    predicted = profiler.get_feature_regressions(
                        report_files[0], list_name
                    )

                    results = ConfusionMatrix(
                        map_to_positive(ground_truth),
                        map_to_negative(ground_truth),
                        map_to_positive(predicted), map_to_negative(predicted)
                    )

                    new_row[f"precision"] = results.precision()
                    new_row[f"recall"] = results.recall()
                    new_row[f"baccuracy"] = results.balanced_accuracy()
                    new_row[f"RegressedFeatures"] = len(
                        map_to_positive(ground_truth)
                    )

                    table_rows.append(new_row)

    return pd.DataFrame(table_rows)


def load_overhead_data(
    case_studies: tp.List[CaseStudy], profilers: tp.List[Profiler]
) -> pd.DataFrame:
    """Loads overhead measurement data for the given cases studies and computes
    overhead metrics that where introduced by the different profilers."""
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
            'time': overhead_ground_truth.mean_time(),
            'memory': overhead_ground_truth.mean_memory(),
            'major_page_faults': overhead_ground_truth.mean_major_page_faults(),
            'minor_page_faults': overhead_ground_truth.mean_minor_page_faults(),
            'fs_inputs': overhead_ground_truth.mean_fs_inputs(),
            'fs_outputs': overhead_ground_truth.mean_fs_outputs(),
            'overhead_time': 0,
            'overhead_memory': 0,
            'overhead_major_page_faults': 0,
            'overhead_minor_page_faults': 0,
            'overhead_fs_inputs': 0,
            'overhead_fs_outputs': 0
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
                memory_diff = profiler_overhead.config_wise_memory_diff(
                    overhead_ground_truth
                )
                major_page_faults_diff = \
                    profiler_overhead.config_wise_major_page_faults_diff(
                        overhead_ground_truth
                    )
                minor_page_faults_diff = \
                    profiler_overhead.config_wise_minor_page_faults_diff(
                        overhead_ground_truth
                    )
                fs_inputs_diff = profiler_overhead.config_wise_fs_inputs_diff(
                    overhead_ground_truth
                )
                fs_outputs_diff = profiler_overhead.config_wise_fs_outputs_diff(
                    overhead_ground_truth
                )

                new_row['time'] = profiler_overhead.mean_time()
                new_row['overhead_time'] = np.mean(list(time_diff.values()))

                new_row['memory'] = profiler_overhead.mean_memory()
                new_row['overhead_memory'] = np.mean(list(memory_diff.values()))

                new_row['major_page_faults'
                       ] = profiler_overhead.mean_major_page_faults()
                new_row['overhead_major_page_faults'] = np.mean(
                    list(major_page_faults_diff.values())
                )

                new_row['minor_page_faults'
                       ] = profiler_overhead.mean_minor_page_faults()
                new_row['overhead_minor_page_faults'] = np.mean(
                    list(minor_page_faults_diff.values())
                )

                new_row['fs_inputs'] = profiler_overhead.mean_fs_inputs()
                new_row['overhead_fs_inputs'] = np.mean(
                    list(fs_inputs_diff.values())
                )

                new_row['fs_outputs'] = profiler_overhead.mean_fs_outputs()
                new_row['overhead_fs_outputs'] = np.mean(
                    list(fs_outputs_diff.values())
                )
            else:
                new_row['time'] = np.nan
                new_row['overhead_time'] = np.nan

                new_row['memory'] = np.nan
                new_row['overhead_memory'] = np.nan

                new_row['major_page_faults'] = np.nan
                new_row['overhead_major_page_faults'] = np.nan

                new_row['minor_page_faults'] = np.nan
                new_row['overhead_minor_page_faults'] = np.nan

                new_row['fs_inputs'] = np.nan
                new_row['overhead_fs_inputs'] = np.nan

                new_row['fs_outputs'] = np.nan
                new_row['overhead_fs_outputs'] = np.nan

            table_rows.append(new_row)

    return pd.DataFrame(table_rows)


def total_feature_time_from_pim(pim_data: tp.DefaultDict[str, tp.List[int]]):
    pim_totals: tp.List[tp.List[int]] = [
        values for feature, values in pim_data.items() if feature != "Base"
    ]

    return [sum(values) for values in zip(*pim_totals)]


def extract_measured_times(time_report, requested_features=None):
    acc_pim: tp.DefaultDict[str, tp.List[int]] = defaultdict(list)
    if isinstance(time_report, TimeReportAggregate):
        return time_report.measurements_wall_clock_time
    elif isinstance(time_report, TEFReportAggregate):
        for report in time_report.reports():
            pim = get_feature_performance_from_tef_report(report)

            for feature, value in pim.items():
                acc_pim[feature].append(value)

    elif isinstance(time_report, PerfInfluenceTraceReportAggregate):
        for old_pim_report in time_report.reports():
            per_report_acc_pim: tp.DefaultDict[str, int] = defaultdict(int)
            for region_inter in old_pim_report.region_interaction_entries:
                name = get_interactions_from_fr_string(
                    old_pim_report._translate_interaction(
                        region_inter.interaction
                    )
                )
                per_report_acc_pim[name] += region_inter.time

            for name, time_value in per_report_acc_pim.items():
                acc_pim[name].append(time_value)

    else:
        print(f"Uncovered report type: {type(time_report)}")
        return [np.nan]

    if requested_features:
        return acc_pim[requested_features]

    return total_feature_time_from_pim(acc_pim)
