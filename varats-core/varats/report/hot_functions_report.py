import typing as tp
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from varats.experiment.workload_util import WorkloadSpecificReportAggregate
from varats.report.report import BaseReport, ReportAggregate


@dataclass
class XRayFunctionWrapper:
    name: str
    count: int
    sum_time: float
    self_time: float

    def __str__(self) -> str:
        return f"{self.name}[count={self.count}, sum={self.sum_time}, self={self.self_time}]"

    def __repr__(self) -> str:
        return str(self)


def _ns_to_seconds(ns: int) -> float:
    return float(ns) / 1000000000


def _seconds_to_ns(seconds: int) -> float:
    return float(seconds) * 1000000000


class HotFunctionReport(BaseReport, shorthand="HFR", file_type=".csv"):
    """Report class to load and evaluate the hot function data."""

    MAX_TRACK_FUNCTIONS = 50

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.__function_data = pd.read_csv(path)

    @staticmethod
    def __create_function_wrapper(
        function_data: pd.Series
    ) -> XRayFunctionWrapper:
        return XRayFunctionWrapper(
            name=function_data["function"],
            count=function_data["count"],
            sum_time=_ns_to_seconds(function_data["sum"]),
            self_time=_ns_to_seconds(function_data["self"])
        )

    @property
    def total_time(self) -> float:
        return _ns_to_seconds(self.__function_data["sum"].max())

    def function(self, function_name: str) -> XRayFunctionWrapper:
        return self.__create_function_wrapper(
            self.__function_data[self.__function_data["function"] ==
                                 function_name]
        )

    def top_n_functions(self, limit: int = 10) -> tp.List[XRayFunctionWrapper]:
        """Determines the `n` hottest functions in which the most time was
        spent."""
        self.__function_data.sort_values(
            by='self', ascending=False, inplace=True
        )
        return [
            self.__create_function_wrapper(row)
            for _, row in self.__function_data.head(limit).iterrows()
        ]

    def hot_functions(self, threshold: int = 2) -> tp.List[XRayFunctionWrapper]:
        """
        Args:
            threshold: min percentage a function needs as self time to count as hot
        """
        if threshold < 0 or threshold > 100:
            raise ValueError(
                "Threshold value needs to be in the range [0,...,100] "
                f"but was {threshold}"
            )

        self.__function_data.sort_values(
            by='self', ascending=False, inplace=True
        )

        total_time_tracked = self.__function_data["sum"].max()

        if total_time_tracked < _seconds_to_ns(1):
            print("Ignoring measurement with total time < 1s.")
            return []

        if threshold == 0:
            self_time_cutoff = 0
        else:
            self_time_cutoff = (total_time_tracked * threshold) / 100

        return [
            self.__create_function_wrapper(row)
            for _, row in self.__function_data.iterrows()
            if row["self"] > self_time_cutoff
        ]

    def print_full_dump(self) -> None:
        print(f"{self.__function_data}")


class WLHotFunctionAggregate(
    WorkloadSpecificReportAggregate[HotFunctionReport],
    shorthand="WL" + HotFunctionReport.SHORTHAND + ReportAggregate.SHORTHAND,
    file_type=ReportAggregate.FILE_TYPE
):

    def __init__(self, path: Path) -> None:
        super().__init__(path, HotFunctionReport)

    def total_times(self, workload_name: str) -> tp.List[float]:
        return [report.total_time for report in self.reports(workload_name)]

    def dump_all_reports(self) -> None:
        """Dumps the contents of all loaded hot functions reports."""
        for wl_name in self.workload_names():
            for report in self.reports(wl_name):
                report.print_full_dump()

    def hot_functions_per_workload(
        self,
        threshold: int = 2
    ) -> tp.Dict[str, tp.Dict[str, tp.List[XRayFunctionWrapper]]]:
        """
        Args:
            threshold: min percentage a function needs as self time to count as hot
        """
        res: tp.Dict[str, tp.Dict[str, tp.List[XRayFunctionWrapper]]] = {}
        for wl_name in self.workload_names():
            wl_hot_funcs: tp.Dict[
                str, tp.List[XRayFunctionWrapper]] = defaultdict(list)
            wl_reports = self.reports(wl_name)
            for report in wl_reports:
                for func in report.hot_functions(threshold=threshold):
                    wl_hot_funcs[func.name].append(func)

            # only consider hot functions that are hot in all repetitions
            res[wl_name] = {}
            for func_name, funcs in wl_hot_funcs.items():
                # if len(funcs) == len(wl_reports):
                res[wl_name][func_name] = funcs

        return res
