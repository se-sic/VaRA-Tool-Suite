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


class HotFunctionReport(BaseReport, shorthand="HFR", file_type=".csv"):
    """Report class to load and evaluate the hot function data."""

    MAX_TRACK_FUNCTIONS = 50

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.__function_data = read_csv(path)

    def top_n_functions(self, limit: int = 10) -> tp.List[XRayFunctionWrapper]:
        """Determines the `n` hottest functions in which the most time was
        spent."""
        self.__function_data.sort_values(
            by='sum', ascending=False, inplace=True
        )
        return [
            XRayFunctionWrapper(
                name=row["function"], count=row['count'], sum_time=row["sum"]
            ) for _, row in self.__function_data.head(limit).iterrows()
        ]

    def hot_functions(self, threshold: int = 2) -> tp.List[XRayFunctionWrapper]:
        """
        Args:
            threshold: min percentage a function needs as total
                        time to count as hot
        """
        if threshold < 0 or threshold > 100:
            raise ValueError(
                "Threshold value needs to be in the range [0,...,100] "
                f"but was {threshold}"
            )

        self.__function_data.sort_values(
            by='sum', ascending=False, inplace=True
        )
        # The total time tracked only includes time spend in the top n
        # (MAX_TRACK_FUNCTIONS) functions
        total_time_tracked = self.__function_data["sum"].max()

        if threshold == 0:
            sum_time_cutoff = 0
        else:
            sum_time_cutoff = (total_time_tracked * threshold) / 100

        return [
            XRayFunctionWrapper(
                name=row["function"], count=row['count'], sum_time=row["sum"]
            )
            for _, row in self.__function_data.iterrows()
            if row["sum"] > sum_time_cutoff
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
        """Dumps the contents of all loaded hot functions reports."""
        for wl_name in self.workload_names():
            for report in self.reports(wl_name):
                report.print_full_dump()

    def hot_functions_per_workload(
        self, threshold: int = 2
    ) -> tp.Dict[str, tp.List[XRayFunctionWrapper]]:
        """
        Args:
            threshold: min percentage a function needs as
                        total time to count as hot
        """
        res: tp.Dict[str, tp.List[XRayFunctionWrapper]] = {}
        for wl_name in self.workload_names():
            # TODO: repetition handling
            for report in self.reports(wl_name):
                res[wl_name] = report.hot_functions(threshold=threshold)

        return res
