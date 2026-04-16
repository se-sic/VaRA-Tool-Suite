"""Shared data aggregation function for analyzing feature performance."""
import abc
import logging
import traceback
import typing as tp
from collections import defaultdict

import numpy as np
import pandas as pd
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
#from varats.data.reports.tef_feature_identifier_report import TEFFeatureIdentifierReport
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
    get_feature_performance_from_tef_report,
    get_interactions_from_fr_string,
)
from varats.revision.revisions import get_processed_revisions_files
from varats.utils.git_util import FullCommitHash

LOG = logging.getLogger(__name__)

REPORT_CACHE = {}


def _get_mprtef_report_cached(
    report_path: ReportFilepath
) -> MultiPatchReport[TEFReportAggregate]:
    if report_path.full_path() not in REPORT_CACHE:
        REPORT_CACHE[
            report_path.full_path()
        ] = MultiPatchReport(report_path.full_path(), TEFReportAggregate)
    else:
        pass
        #print(
        #    f"Using internally cached TEF report for {report_path.full_path()}"
        #)

    return REPORT_CACHE[report_path.full_path()]


class Profiler():
    """Profiler interface to add different profilers to the evaluation."""

    def __init__(
        self,
        name: str,
        experiment: tp.Type[FeatureExperiment],
        overhead_experiment: tp.Type[FeatureExperiment],
        report_type: tp.Type[BaseReport],
        relative_cut_off: float = 0.01,
        absolute_cut_off: int = 100
    ) -> None:
        self.__name = name
        self.__experiment = experiment
        self.__overhead_experiment = overhead_experiment
        self.__report_type = report_type
        self.__relative_cut_off = relative_cut_off
        self.__absolute_cut_off = absolute_cut_off

    @property
    def name(self) -> str:
        """Name of the profiler used."""
        return self.__name

    @property
    def experiment(self) -> tp.Type[FeatureExperiment]:
        """Experiment used to produce this profilers information."""
        return self.__experiment

    @property
    def overhead_experiment(self) -> tp.Type[FeatureExperiment]:
        """Experiment used to produce overhead data that this profilers produced
        when collecting information."""
        return self.__overhead_experiment

    @property
    def report_type(self) -> tp.Type[BaseReport]:
        """Report type used to load this profilers information."""
        return self.__report_type

    @property
    def relative_cut_off(self) -> float:
        """Returns the relative cut off in percent below which regressions
        should not be considered."""
        return self.__relative_cut_off

    @property
    def absolute_cut_off(self) -> int:
        """Returns the absolute cut off in milliseconds below which regressions
        should not be considered."""
        return self.__absolute_cut_off

    def set_absolute_cut_off(self, cut_off: int) -> None:
        """Sets the absolute cut off in milliseconds below which regressions
        should not be considered."""
        if cut_off <= 0:
            raise ValueError("Cut off must be non-negative")
        self.__absolute_cut_off = cut_off

    def set_relative_cut_off(self, cut_off: float) -> None:
        """Sets the relative cut off in percent below which regressions should
        not be considered."""
        if cut_off < 0 or cut_off > 1:
            raise ValueError("Cut off must be between 0 and 1")
        self.__relative_cut_off = cut_off

    def _is_significantly_different(
        self, old_values: tp.Sequence[tp.Union[float, int]],
        new_values: tp.Sequence[tp.Union[float, int]]
    ) -> bool:
        """Checks if there is a significant difference between old and new
        values."""
        return self.__ttest(old_values, new_values)

    def __ttest(  # pylint: disable=W0238
        self, old_values: tp.Sequence[tp.Union[float, int]],
        new_values: tp.Sequence[tp.Union[float, int]]
    ) -> bool:
        """Implements t-test."""
        ttest_res = ttest_ind(old_values, new_values)

        if ttest_res.pvalue < 0.05:
            return True

        return False

    def __cliffs_delta(  # pylint: disable=W0238
        self, old_values: tp.Sequence[tp.Union[float, int]],
        new_values: tp.Sequence[tp.Union[float, int]]
    ) -> bool:
        """Implements cliffs_delta test."""
        cdelta_val, _ = cliffs_delta(old_values, new_values)

        # if res == "large":
        if abs(cdelta_val) > 0.7:
            return True

        return False

    def _is_feature_relevant(
        self, old_measurements: tp.List[int], new_measurements: tp.List[int]
    ) -> bool:
        """Check if a feature can be ignored for regression checking as it's
        time measurements seem not relevant."""
        old_mean = np.mean(old_measurements)
        new_mean = np.mean(new_measurements)

        if old_mean < self.absolute_cut_off and \
                new_mean < self.absolute_cut_off:
            return False

        old_rel_cut_off = old_mean * self.relative_cut_off
        abs_mean_diff = abs(old_mean - new_mean)
        if abs_mean_diff < old_rel_cut_off:
            return False

        return True

    def _precise_pim_regression_check(
        self, baseline_pim: tp.DefaultDict[str, tp.List[int]],
        current_pim: tp.DefaultDict[str, tp.List[int]]
    ) -> bool:
        """Compute if there was a regression in one of the feature terms of the
        model between the current and the baseline, using a Mann-Whitney U
        test."""
        is_regression = False

        for feature, old_values in baseline_pim.items():
            if feature in current_pim:
                if feature == "Base":
                    # The regression should be identified in actual feature code
                    continue

                new_values = current_pim[feature]

                # Skip features that seem not to be relevant
                # for regressions testing
                if not self._is_feature_relevant(old_values, new_values):
                    continue

                is_regression = is_regression or \
                    self._is_significantly_different(
                        old_values, new_values
                    )
            else:
                if np.mean(old_values) > self.absolute_cut_off:
                    print(
                        f"Could not find feature {feature} in new trace. "
                        f"({np.mean(old_values)}us lost)"
                    )

        return is_regression

    def _sum_pim_regression_check(
        self, baseline_pim: tp.DefaultDict[str, tp.List[int]],
        current_pim: tp.DefaultDict[str, tp.List[int]]
    ) -> bool:
        """
        Compute if there was a regression in the sum of the features in the
        model between the current and the baseline.

        The comparision is done through a Mann-Whitney U test.
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
            # How did we get here?
            return False

        mean_baseline = np.mean(baseline_pim_total)
        mean_diff = abs(mean_baseline - np.mean(current_pim_total))
        if mean_diff < self.absolute_cut_off or \
                mean_diff < mean_baseline * self.relative_cut_off:
            return False

        return self._is_significantly_different(
            baseline_pim_total, current_pim_total
        )

    def pim_regression_check(
        self, baseline_pim: tp.DefaultDict[str, tp.List[int]],
        current_pim: tp.DefaultDict[str, tp.List[int]]
    ) -> bool:
        """Compares two pims and determines if there was a regression between
        the baseline and current."""
        return self._precise_pim_regression_check(baseline_pim, current_pim)

    def default_regression_check(
        self, old_values: tp.Sequence[tp.Union[float, int]],
        new_values: tp.Sequence[tp.Union[float, int]]
    ) -> bool:
        """Checks if there is a significant difference between old and new
        values."""
        return self._is_significantly_different(old_values, new_values)

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
            fpp.MPRTEFAggregate
        )

    def is_regression(
        self, report_path: ReportFilepath, patch_name: str
    ) -> bool:
        """Checks if there was a regression between the old an new data."""
        multi_report = _get_mprtef_report_cached(report_path)

        old_acc_pim: tp.DefaultDict[str, tp.List[int]] = defaultdict(list)
        for old_tef_report in multi_report.get_baseline_report().reports():
            pim = get_feature_performance_from_tef_report(old_tef_report)
            for feature, value in pim.items():
                old_acc_pim[feature].append(value)

        new_acc_pim: tp.DefaultDict[str, tp.List[int]] = defaultdict(list)
        opt_mr = multi_report.get_report_for_patch(patch_name)
        if not opt_mr:
            print(f"Missing TEF Report in {report_path} for patch {patch_name}")
            return False

        for new_tef_report in opt_mr.reports():
            pim = get_feature_performance_from_tef_report(new_tef_report)
            for feature, value in pim.items():
                new_acc_pim[feature].append(value)

        return self.pim_regression_check(old_acc_pim, new_acc_pim)


class PIMTracer(Profiler):
    """Profiler mapper implementation for the vara performance-influence-model
    tracer."""

    def __init__(self) -> None:
        super().__init__(
            "PIMTracer", fpp.PIMProfileRunner, fpp.PIMProfileOverheadRunner,
            fpp.MPRPIMAggregate
        )

    @staticmethod
    def __aggregate_pim_data(
        reports: tp.List[PerfInfluenceTraceReport]
    ) -> tp.DefaultDict[str, tp.List[int]]:
        acc_pim: tp.DefaultDict[str, tp.List[int]] = defaultdict(list)
        for old_pim_report in reports:
            per_report_acc_pim: tp.DefaultDict[str, int] = defaultdict(int)
            for region_inter in old_pim_report.region_interaction_entries:
                region_names = old_pim_report._translate_interaction(
                    region_inter.interaction, new_sep=","
                )
                name = get_interactions_from_fr_string(region_names)
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
            print(
                f"Missing new PIM report in file {report_path} for patch {patch_name}"
            )
            return False

        new_acc_pim = self.__aggregate_pim_data(opt_mr.reports())

        return self.pim_regression_check(old_acc_pim, new_acc_pim)


class EbpfTraceTEF(Profiler):
    """Profiler mapper implementation for the vara tef tracer."""

    def __init__(self) -> None:
        super().__init__(
            "eBPFTrace", fpp.EbpfTraceTEFProfileRunner,
            fpp.EbpfTraceTEFOverheadRunner, fpp.MPRTEFAggregate
        )

    def is_regression(
        self, report_path: ReportFilepath, patch_name: str
    ) -> bool:
        """Checks if there was a regression between the old an new data."""
        multi_report = _get_mprtef_report_cached(report_path)

        old_acc_pim: tp.DefaultDict[str, tp.List[int]] = defaultdict(list)
        for old_tef_report in multi_report.get_baseline_report().reports():
            pim = get_feature_performance_from_tef_report(old_tef_report)
            for feature, value in pim.items():
                old_acc_pim[feature].append(value)

        new_acc_pim: tp.DefaultDict[str, tp.List[int]] = defaultdict(list)
        opt_mr = multi_report.get_report_for_patch(patch_name)
        if not opt_mr:
            print(
                f"Missing new EBPF report in file {report_path} for patch {patch_name}"
            )
            return False

        for new_tef_report in opt_mr.reports():
            pim = get_feature_performance_from_tef_report(new_tef_report)
            for feature, value in pim.items():
                new_acc_pim[feature].append(value)

        return self.pim_regression_check(old_acc_pim, new_acc_pim)


class Baseline(Profiler):
    """Profiler mapper implementation for the black-box baseline."""

    def __init__(self) -> None:
        super().__init__(
            "Base", fpp.BlackBoxBaselineRunner, fpp.BlackBoxOverheadBaseline,
            fpp.MPRTimeReportAggregate
        )

    def is_regression(
        self, report_path: ReportFilepath, patch_name: str
    ) -> bool:
        time_reports = load_mpr_time_report_aggregate(report_path)

        old_time = time_reports.get_baseline_report()
        new_time = time_reports.get_report_for_patch(patch_name)
        if not new_time:
            print(
                f"Missing new time report for '{patch_name}' in file {report_path}"
            )
            return False
            #raise LookupError(f"Missing new time report in file {report_path}")

        # Cut off regressions smaller than 100ms
        req_diff = self.absolute_cut_off / 1000
        if np.mean(old_time.measurements_wall_clock_time
                  ) == np.mean(new_time.measurements_wall_clock_time):
            return False

        if abs(
            np.mean(old_time.measurements_wall_clock_time) -
            np.mean(new_time.measurements_wall_clock_time)
        ) < req_diff:
            return False

        return self.default_regression_check(
            old_time.measurements_wall_clock_time,
            new_time.measurements_wall_clock_time
        )


def get_patch_names(case_study: CaseStudy) -> tp.List[str]:
    """Looks up all patch names from the given case study."""
    report_files = get_processed_revisions_files(
        case_study.project_name,
        fpp.BlackBoxBaselineRunner,
        fpp.MPRTimeReportAggregate,
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

        baseline_prof = Baseline()
        ground_truth[config_id] = baseline_prof.is_regression(
            report_files[0], patch_name
        )

    return ground_truth


def map_to_positive_config_ids(reg_dict: tp.Dict[int, bool]) -> tp.List[int]:
    return [config_id for config_id, value in reg_dict.items() if value is True]


def map_to_negative_config_ids(reg_dict: tp.Dict[int, bool]) -> tp.List[int]:
    return [
        config_id for config_id, value in reg_dict.items() if value is False
    ]


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
            # Print exception information but continue working on the plot/table
            print(
                f"FAILURE: Skipping {config_id=} of {project_name=}, "
                f"profiler={profiler.name}"
            )
            print(exception)
            print(traceback.format_exc())

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
                        len(map_to_positive_config_ids(ground_truth))
                        if ground_truth else -1
                }

                predicted = compute_profiler_predictions(
                    profiler, project_name, case_study,
                    case_study.get_config_ids_for_revision(rev), patch_name
                )

                if ground_truth and predicted:
                    results = ConfusionMatrix(
                        map_to_positive_config_ids(ground_truth),
                        map_to_negative_config_ids(ground_truth),
                        map_to_positive_config_ids(predicted),
                        map_to_negative_config_ids(predicted)
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
            print(
                f"No baseline data for {case_study.project_name}, generating dummy data"
            )
            table_rows.extend([{
                'CaseStudy': project_name,
                'Profiler': p,
                'time': np.nan,
                'memory': np.nan,
                'major_page_faults': np.nan,
                'minor_page_faults': np.nan,
                'fs_inputs': np.nan,
                'fs_outputs': np.nan,
                'overhead_time': np.nan,
                'overhead_memory': np.nan,
                'overhead_major_page_faults': np.nan,
                'overhead_minor_page_faults': np.nan,
                'overhead_fs_inputs': np.nan,
                'overhead_fs_outputs': np.nan
            } for p in ["Base"] + [profiler.name for profiler in profilers]])
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


def get_regressed_features_gt(
    base_features: tp.Iterable[str],
    ground_truth_report: TEFFeatureIdentifierReport, patches: tp.Iterable[str]
) -> tp.Dict[str, bool]:
    ground_truth = {}

    for feature in base_features:
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


def _precise_pim_feature_regression_check(
    baseline_pim: tp.DefaultDict[str, tp.List[int]],
    current_pim: tp.DefaultDict[str, tp.List[int]],
    profiler: Profiler,
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
            if not profiler._is_feature_relevant(old_values, new_values):
                is_regression[feature] = False
                continue

            ttest_res = ttest_ind(old_values, new_values)

            if ttest_res.pvalue < 0.05:
                is_regression[feature] = True
            else:
                is_regression[feature] = False
        else:
            if np.mean(old_values) > profiler.absolute_cut_off:
                print(
                    f"Could not find feature {feature} in new trace. "
                    f"({np.mean(old_values)}us lost)"
                )
            is_regression[feature] = False
            # TODO: how to handle this?
            # raise NotImplementedError()
            # is_regression = True

    return is_regression


def get_feature_regressions_xray(
    report_path: ReportFilepath, patch_name: str, profiler: VXray
) -> tp.Dict[str, bool]:
    """Gets the predicted regressed features from the xray report."""
    multi_report = MultiPatchReport(report_path.full_path(), TEFReportAggregate)
    old_acc_pim: tp.DefaultDict[str, tp.List[int]] = defaultdict(list)
    for old_tef_report in multi_report.get_baseline_report().reports():
        pim = get_feature_performance_from_tef_report(old_tef_report)
        for feature, value in pim.items():
            old_acc_pim[feature].append(value)

    new_acc_pim: tp.DefaultDict[str, tp.List[int]] = defaultdict(list)
    opt_mr = multi_report.get_report_for_patch(patch_name)
    if not opt_mr:
        #raise NotImplementedError()
        print(f"{patch_name=};{report_path.report_filename.project_name=}")
        return dict()

    for new_tef_report in opt_mr.reports():
        pim = get_feature_performance_from_tef_report(new_tef_report)
        for feature, value in pim.items():
            new_acc_pim[feature].append(value)

    return _precise_pim_feature_regression_check(
        old_acc_pim, new_acc_pim, profiler
    )


def get_feature_regressions_pim(
    report_path: ReportFilepath, patch_name: str, profiler: PIMTracer
) -> tp.Dict[str, bool]:
    """Gets the predicted regressed features from the pimtracer report."""
    multi_report = MultiPatchReport(
        report_path.full_path(), PerfInfluenceTraceReportAggregate
    )

    old_acc_pim = profiler._PIMTracer__aggregate_pim_data(
        multi_report.get_baseline_report().reports()
    )

    opt_mr = multi_report.get_report_for_patch(patch_name)
    if not opt_mr:
        # raise NotImplementedError()
        print(f"{patch_name=};{report_path.report_filename.project_name=}")
        return dict()

    new_acc_pim = profiler._PIMTracer__aggregate_pim_data(opt_mr.reports())

    results = _precise_pim_feature_regression_check(
        old_acc_pim, new_acc_pim, profiler
    )

    return results


def get_feature_regressions_ebpf(
    report_path: ReportFilepath, patch_name: str, profiler: EbpfTraceTEF
) -> tp.Dict[str, bool]:
    """Gets the predicted regressed features from the ebpf report."""
    multi_report = MultiPatchReport(report_path.full_path(), TEFReportAggregate)
    old_acc_pim: tp.DefaultDict[str, tp.List[int]] = defaultdict(list)
    for old_tef_report in multi_report.get_baseline_report().reports():
        pim = get_feature_performance_from_tef_report(old_tef_report)
        for feature, value in pim.items():
            old_acc_pim[feature].append(value)

    new_acc_pim: tp.DefaultDict[str, tp.List[int]] = defaultdict(list)
    opt_mr = multi_report.get_report_for_patch(patch_name)
    if not opt_mr:
        # raise NotImplementedError()
        print(f"{patch_name=};{report_path.report_filename.project_name=}")
        return dict()

    for new_tef_report in opt_mr.reports():
        pim = get_feature_performance_from_tef_report(new_tef_report)
        for feature, value in pim.items():
            new_acc_pim[feature].append(value)

    return _precise_pim_feature_regression_check(
        old_acc_pim, new_acc_pim, profiler
    )


_PROFILER_FEATURE_REGRESSIONS = {
    "WXray": get_feature_regressions_xray,
    "PIMTracer": get_feature_regressions_pim,
    "eBPFTrace": get_feature_regressions_ebpf
}


def load_precision_whitebox_data(
    case_studies: tp.List[CaseStudy], profilers: tp.List[Profiler]
) -> pd.DataFrame:
    table_rows = []

    for cs in case_studies:
        if cs.project_name != "DunePerfRegression":
            print(f"Skipping {cs.project_name}...")
            #continue
        print(f"Processing case study {cs.project_name}...")
        rev = cs.revisions[0]

        for config_id in cs.get_config_ids_for_revision(rev):
            print(f"Processing config id {config_id}...")
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
                    print(
                        f"Should only be one ({profiler.name=},{cs.project_name=},{config_id=})"
                    )
                    continue
                    # raise AssertionError("Should only be one")

                profiler_report_files[profiler] = (
                    MultiPatchReport(
                        report_files[0].full_path(),
                        PerfInfluenceTraceReportAggregate
                        if profiler.name == "PIMTracer" else TEFReportAggregate
                    ), report_files[0]
                )

            if len(ground_truth_report_files) != 1:
                print("Invalid number of reports from TEFIdentifier")
                continue

            ground_truth_report = TEFFeatureIdentifierReport(
                ground_truth_report_files[0].full_path()
            )

            for patch in ground_truth_report.patch_names:
                relevant_patch = patch.removesuffix("detect") + "1000ms"
                for profiler in profilers:
                    report_file, rpf = profiler_report_files[profiler]

                    all_features = []

                    if profiler.name == "PIMTracer":
                        base_report: tp.Iterable[
                            PerfInfluenceTraceReportAggregate
                        ] = report_file.get_baseline_report().reports()
                        for pim_report in base_report:
                            pim_report: PerfInfluenceTraceReport
                            all_features = [
                                get_interactions_from_fr_string(
                                    pim_report._translate_interaction(
                                        f.interaction, new_sep=","
                                    ),
                                    sep=","
                                ) for f in pim_report.region_interaction_entries
                            ]
                            # Deduplication of nested features
                            all_features = [
                                "*".join(sorted(list(set(feature.split("*")))))
                                for feature in all_features
                            ]
                    else:
                        base_report = report_file.get_baseline_report().reports(
                        )
                        for tef_report in base_report:
                            pim = get_feature_performance_from_tef_report(
                                tef_report
                            )
                            all_features.extend(pim.keys())

                    all_features = list(set(all_features))

                    regressed_features_gt = get_regressed_features_gt(
                        all_features, ground_truth_report, [relevant_patch]
                    )

                    regressed_features_predicted = _PROFILER_FEATURE_REGRESSIONS[
                        profiler.name](rpf, relevant_patch, profiler)

                    for feature in regressed_features_gt:
                        if feature not in regressed_features_predicted:
                            print(
                                f"Feature {feature} missing in predicted for "
                                f"{profiler.name=}, {cs.project_name=}, "
                                f"{config_id=}, {patch=}"
                            )
                            regressed_features_predicted[feature] = False

                    new_row = {
                        'CaseStudy': cs.project_name,
                        'Patch': relevant_patch,
                        'ConfigID': config_id,
                        'Profiler': profiler.name
                    }

                    results = ConfusionMatrix(
                        map_to_positive_config_ids(regressed_features_gt),
                        map_to_negative_config_ids(regressed_features_gt),
                        map_to_positive_config_ids(
                            regressed_features_predicted
                        ),
                        map_to_negative_config_ids(
                            regressed_features_predicted
                        )
                    )

                    new_row[f"precision"] = results.precision()
                    new_row[f"recall"] = results.recall()
                    new_row[f"baccuracy"] = results.balanced_accuracy()
                    new_row[f"RegressedFeatures"] = len(
                        map_to_positive_config_ids(regressed_features_gt)
                    )
                    new_row["expected"] = results.actual_positive
                    new_row["TP"] = results.getTPs()
                    new_row["FP"] = results.getFPs()
                    new_row["TN"] = results.getTNs()
                    new_row["FN"] = results.getFNs()

                    table_rows.append(new_row)

    return pd.DataFrame(table_rows)
