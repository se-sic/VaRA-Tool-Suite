"""Module for the FeaturePerfPrecision table."""
import abc
import typing as tp

import pandas as pd

import varats.experiments.vara.feature_perf_precision as fpp
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.experiments.vara.feature_perf_runner import FeaturePerfRunner
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.report import BaseReport
from varats.report.tef_report import TEFReport
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator


def get_regressing_config_ids_GT(case_study: CaseStudy) -> tp.Dict[int, bool]:
    #if case_study.project_name == "SynthSAContextSensitivity":
    return {
        0: True,
        1: True,
        2: True,
        3: True,
        4: False,
        5: False,
        6: False,
        7: False
    }

    # raise NotImplementedError()
    return {}


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


class VXray(Profiler):

    def __init__(self) -> None:
        # TODO: fix with actual
        super().__init__("WXray", fpp.TEFProfileRunner, TEFReport)


def compute_profiler_predictions(
    profiler: Profiler, project_name: str, case_study: CaseStudy
) -> tp.Dict[int, bool]:
    report_files = get_processed_revisions_files(
        project_name, profiler.experiment, profiler.report_type,
        get_case_study_file_name_filter(case_study)
    )

    return {}


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

            ground_truth = get_regressing_config_ids_GT(case_study)

            new_row = {
                'CaseStudy':
                    project_name,
                'Configs':
                    len(case_study.get_config_ids_for_revision(rev)),
                'RegressedConfigs':
                    len(map_to_positive_config_ids(ground_truth))
            }

            for profiler in profilers:
                # multiple patch cycles
                predicted = compute_profiler_predictions(
                    profiler, project_name, case_study
                )
                predicted = {
                    0: True,
                    1: True,
                    2: False,
                    3: True,
                    4: False,
                    5: True,
                    6: True,
                    7: False
                }

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
