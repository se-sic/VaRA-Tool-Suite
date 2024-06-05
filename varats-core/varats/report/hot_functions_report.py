import typing as tp
from dataclasses import dataclass
from pathlib import Path

from pandas import read_csv

from varats.experiment.workload_util import WorkloadSpecificReportAggregate
from varats.report.report import BaseReport, ReportAggregate


@dataclass
class XRayFunctionWrapper:
    name: str
    count: int
    sum_time: float
    self_time: float


def _ns_to_seconds(ns: int) -> float:
    return float(ns) / 1000000000


def _seconds_to_ns(seconds: int) -> float:
    return float(seconds) * 1000000000


class HotFunctionReport(BaseReport, shorthand="HFR", file_type=".csv"):

    MAX_TRACK_FUNCTIONS = 50

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.__function_data = read_csv(path)

    def top_n_functions(self, limit=10) -> tp.List[XRayFunctionWrapper]:
        self.__function_data.sort_values(
            by='self', ascending=False, inplace=True
        )
        return [
            XRayFunctionWrapper(
                name=row["function"],
                count=row['count'],
                sum_time=_ns_to_seconds(row["sum"]),
                self_time=_ns_to_seconds(row["self"])
            ) for _, row in self.__function_data.head(limit).iterrows()
        ]

    def hot_functions(self, threshold=2) -> tp.List[XRayFunctionWrapper]:
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
            XRayFunctionWrapper(
                name=row["function"],
                count=row['count'],
                sum_time=_ns_to_seconds(row["sum"]),
                self_time=_ns_to_seconds(row["self"])
            )
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

    def dump_all_reports(self) -> None:
        for wl_name in self.workload_names():
            for report in self.reports(wl_name):
                report.print_full_dump()

    def hot_functions_per_workload(
        self, threshold=2
    ) -> tp.Dict[str, tp.List[XRayFunctionWrapper]]:
        """
        Args:
            threshold: min percentage a function needs as self time to count as hot
        """
        res: tp.Dict[str, tp.List[XRayFunctionWrapper]] = {}
        for wl_name in self.workload_names():
            # TODO: repetition handling
            for report in self.reports(wl_name):
                res[wl_name] = report.hot_functions(threshold=threshold)

        return res
