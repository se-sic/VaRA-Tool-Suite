"""Module for the FeaturePerfPrecision table."""
import abc
import shutil
import tempfile
import typing as tp
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ttest_ind

import varats.experiments.vara.feature_perf_precision as fpp
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.experiments.vara.feature_perf_runner import FeaturePerfRunner
from varats.jupyterhelper.file import load_tef_report
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.gnu_time_report import TimeReportAggregate
from varats.report.report import BaseReport, ReportFilepath
from varats.report.tef_report import TEFReport, TraceEvent, TraceEventType
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
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


def get_regressing_config_ids_gt(
    project_name: str, case_study: CaseStudy, rev: FullCommitHash
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
                f"Could not find profiling data. {config_id=}, "
                f"profiler=Baseline"
            )
            return None

        time_reports = fpp.MPRTRA(report_files[0].full_path())

        old_time = time_reports.get_old_report()
        new_time = time_reports.get_new_report()

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


class ClassificationResults:
    """Helper class to automatically calculate classification results."""

    def __init__(
        self, actual_positive_values: tp.List[tp.Any],
        actual_negative_values: tp.List[tp.Any],
        predicted_positive_values: tp.List[tp.Any],
        predicted_negative_values: tp.List[tp.Any]
    ) -> None:
        self.__actual_positive_values = actual_positive_values
        self.__actual_negative_values = actual_negative_values
        self.__predicted_positive_values = predicted_positive_values
        self.__predicted_negative_values = predicted_negative_values

    @property
    def P(self) -> int:  # pylint: disable=C0103
        return len(self.__actual_positive_values)

    @property
    def N(self) -> int:  # pylint: disable=C0103
        return len(self.__actual_negative_values)

    @property
    def PP(self) -> int:  # pylint: disable=C0103
        return len(self.__predicted_positive_values)

    @property
    def PN(self) -> int:  # pylint: disable=C0103
        return len(self.__predicted_negative_values)

    @property
    def TP(self) -> int:  # pylint: disable=C0103
        return len(
            set(self.__actual_positive_values
               ).intersection(self.__predicted_positive_values)
        )

    @property
    def TN(self) -> int:  # pylint: disable=C0103
        return len(
            set(self.__actual_negative_values
               ).intersection(self.__predicted_negative_values)
        )

    @property
    def FP(self) -> int:  # pylint: disable=C0103
        return self.PP - self.TP

    @property
    def FN(self) -> int:  # pylint: disable=C0103
        return self.PN - self.TN

    def precision(self) -> float:
        if self.PP == 0:
            return 0.0

        return self.TP / self.PP

    def recall(self) -> float:
        return self.TP / self.P

    def specificity(self) -> float:
        return self.TN / self.N

    def accuracy(self) -> float:
        return (self.TP + self.TN) / (self.P + self.N)

    def balanced_accuracy(self) -> float:
        return (self.recall() + self.specificity()) / 2


class Profiler():
    """Profiler interface to add different profilers to the evaluation."""

    def __init__(
        self, name: str, experiment: tp.Type[FeatureExperiment],
        report_type: tp.Type[BaseReport]
    ) -> None:
        self.__name = name
        self.__experiment = experiment
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
    def report_type(self) -> tp.Type[BaseReport]:
        """Report type used to load this profilers information."""
        return self.__report_type

    @abc.abstractmethod
    def is_regression(self, report_path: ReportFilepath) -> bool:
        """Checks if there was a regression between the old an new data."""


class VXray(Profiler):
    """Profiler mapper implementation for the vara tef tracer."""

    def __init__(self) -> None:
        super().__init__("WXray", fpp.TEFProfileRunner, TEFReport)

    def is_regression(self, report_path: ReportFilepath) -> bool:
        """Checks if there was a regression between the old an new data."""
        is_regression = False

        #        with tempfile.TemporaryDirectory() as tmp_result_dir:
        #            shutil.unpack_archive(
        #                report_path.full_path(), extract_dir=tmp_result_dir
        #            )
        #
        # old_report = None
        # new_report = None
        # for report in Path(tmp_result_dir).iterdir():
        #     # print(f"Zipped: {report=}")
        #     if report.name.endswith("old.json"):
        #         old_report = load_tef_report(report)
        #     else:
        #         new_report = load_tef_report(report)

        # if not old_report or not new_report:
        #     raise AssertionError(
        #         "Reports where missing in the file {report_path=}"
        #     )

        multi_report = fpp.MultiPatchReport(report_path.full_path(), TEFReport)

        old_features = get_feature_performance_from_tef_report(
            multi_report.get_old_report()
        )
        new_features = get_feature_performance_from_tef_report(
            multi_report.get_new_report()
        )

        # TODO: correctly implement how to identify a regression
        for feature, old_value in old_features.items():
            if feature in new_features:
                new_value = new_features[feature]
                if abs(new_value - old_value) > 10000:
                    print(f"Found regression for feature {feature}.")
                    is_regression = True
            else:
                print(f"Could not find feature {feature} in new trace.")
                # TODO: how to handle this?
                is_regression = True

        return is_regression


def compute_profiler_predictions(
    profiler: Profiler, project_name: str, case_study: CaseStudy,
    config_ids: tp.List[int]
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

        result_dict[config_id] = profiler.is_regression(report_files[0])

    print(f"{result_dict=}")
    return result_dict


class FeaturePerfPrecisionTable(Table, table_name="fperf_precision"):
    """Table that compares the precision of different feature performance
    measurement approaches."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()
        profilers: tp.List[Profiler] = [VXray()]

        # Data aggregation
        df = pd.DataFrame()
        table_rows = []

        for case_study in case_studies:
            rev = case_study.revisions[0]
            project_name = case_study.project_name

            ground_truth = get_regressing_config_ids_gt(
                project_name, case_study, rev
            )

            new_row = {
                'CaseStudy':
                    project_name,
                'Configs':
                    len(case_study.get_config_ids_for_revision(rev)),
                'RegressedConfigs':
                    len(map_to_positive_config_ids(ground_truth))
                    if ground_truth else np.nan
            }

            for profiler in profilers:
                # TODO: multiple patch cycles
                predicted = compute_profiler_predictions(
                    profiler, project_name, case_study,
                    case_study.get_config_ids_for_revision(rev)
                )

                if ground_truth and predicted:
                    results = ClassificationResults(
                        map_to_positive_config_ids(ground_truth),
                        map_to_negative_config_ids(ground_truth),
                        map_to_positive_config_ids(predicted),
                        map_to_negative_config_ids(predicted)
                    )
                    new_row[f"{profiler.name}_precision"] = results.precision()
                    new_row[f"{profiler.name}_recall"] = results.recall()
                    new_row[f"{profiler.name}_baccuracy"
                           ] = results.balanced_accuracy()
                else:
                    new_row[f"{profiler.name}_precision"] = np.nan
                    new_row[f"{profiler.name}_recall"] = np.nan
                    new_row[f"{profiler.name}_baccuracy"] = np.nan

            table_rows.append(new_row)
            # df.append(new_row, ignore_index=True)

        df = pd.concat([df, pd.DataFrame(table_rows)])
        df.sort_values(["CaseStudy"], inplace=True)
        df.set_index(
            ["CaseStudy"],
            inplace=True,
        )

        print(f"{df=}")
        colum_setup = [('', 'Configs'), ('', 'RegressedConfigs')]
        for profiler in profilers:
            colum_setup.append((profiler.name, 'Precision'))
            colum_setup.append((profiler.name, 'Recall'))
            colum_setup.append((profiler.name, 'BAcc'))

        print(f"{colum_setup=}")
        df.columns = pd.MultiIndex.from_tuples(colum_setup)

        # Table config

        print(f"{df=}")

        kwargs: tp.Dict[str, tp.Any] = {}
        # if table_format.is_latex():
        #     kwargs["column_format"] = "llr|rr|r|r"

        return dataframe_to_table(
            df,
            table_format,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class FeaturePerfPrecisionTableGenerator(
    TableGenerator, generator_name="fperf-precision", options=[]
):
    """Generator for `FeaturePerfPrecisionTable`."""

    def generate(self) -> tp.List[Table]:
        return [
            FeaturePerfPrecisionTable(self.table_config, **self.table_kwargs)
        ]
