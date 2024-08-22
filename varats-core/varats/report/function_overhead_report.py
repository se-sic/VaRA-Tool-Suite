import logging
import re
import typing as tp
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import yaml

from varats.experiment.workload_util import WorkloadSpecificReportAggregate
from varats.report.multi_patch_report import MultiPatchReport
from varats.report.report import BaseReport, ReportAggregate

LOG = logging.Logger(__name__)


@dataclass
class FunctionOverheadData:
    function_name: str
    samples: int
    overhead: float
    command: str
    dso: str


def _ns_to_seconds(ns: int) -> float:
    return float(ns) / 1000000000


def _seconds_to_ns(seconds: int) -> float:
    return float(seconds) * 1000000000


class FunctionOverheadReport(BaseReport, shorthand="FOR", file_type=".yaml"):

    def __init__(self, path: Path) -> None:
        super().__init__(path)

        self.__function_data: tp.Dict[str, FunctionOverheadData] = {}
        self.__total_samples = 0

        # fix some non-yaml compliant function names
        with open(path, "r+t") as stream:
            text = stream.read()
            replaced_text = re.sub("\s*.*@plt:\n.*\n.*\n.*\n.*", "", text)
            stream.seek(0)
            stream.write(replaced_text)
            stream.truncate()

        with open(path, "r") as stream:
            try:
                raw_report = next(yaml.load_all(stream, Loader=yaml.CLoader))
                self.__total_samples = int(raw_report["total_samples"])

                if raw_functions := raw_report["functions"]:
                    for function_name, raw_function_data in raw_functions.items(
                    ):
                        func_data = FunctionOverheadData(
                            function_name=function_name,
                            samples=int(raw_function_data["samples"]),
                            overhead=raw_function_data["overhead"],
                            command=raw_function_data["command"],
                            dso=raw_function_data["dso"],
                        )
                        self.__function_data[func_data.function_name
                                            ] = func_data

            except (StopIteration, yaml.scanner.ScannerError):
                LOG.warning("Empty report file: %s.", path)

    @property
    def total_samples(self) -> int:
        return self.__total_samples

    def function(self, function_name: str) -> FunctionOverheadData:
        return self.__function_data[function_name]

    def hot_functions(self,
                      threshold: float = 2) -> tp.List[FunctionOverheadData]:
        """
        Retrieve hot functions.

        Args:
            threshold: min overhead percentage a function needs to count as hot
        """
        if threshold < 0 or threshold > 100:
            raise ValueError(
                "Threshold value needs to be in the range [0,...,100] "
                f"but was {threshold}"
            )

        threshold /= 100
        hot_functions: tp.List[FunctionOverheadData] = []

        for function in self.__function_data.values():
            if function.overhead >= threshold:
                hot_functions.append(function)

        return hot_functions


class WLFunctionOverheadReportAggregate(
    WorkloadSpecificReportAggregate[FunctionOverheadReport],
    shorthand="WL" + FunctionOverheadReport.SHORTHAND +
    ReportAggregate.SHORTHAND,
    file_type=ReportAggregate.FILE_TYPE
):

    def __init__(self, path: Path) -> None:
        super().__init__(path, FunctionOverheadReport)

    def hot_functions_per_workload(
        self,
        threshold: float = 2
    ) -> tp.Dict[str, tp.Dict[str, tp.List[FunctionOverheadData]]]:
        """
        Retrieve hot functions grouped by workload.

        Args:
            threshold: min overhead percentage a function needs to count as hot
        """
        res: tp.Dict[str, tp.Dict[str, tp.List[FunctionOverheadData]]] = {}
        for wl_name in self.workload_names():
            wl_hot_funcs: tp.Dict[
                str, tp.List[FunctionOverheadData]] = defaultdict(list)
            wl_reports = self.reports(wl_name)
            for report in wl_reports:
                for func in report.hot_functions(threshold=threshold):
                    wl_hot_funcs[func.function_name].append(func)

            res[wl_name] = wl_hot_funcs

        return res


class MPRWLFunctionOverheadReportAggregate(
    MultiPatchReport[WLFunctionOverheadReportAggregate],
    shorthand="MPR" + WLFunctionOverheadReportAggregate.SHORTHAND,
    file_type=".zip"
):
    """Multi-patch wrapper report for workload specific function overhead
    reports."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, WLFunctionOverheadReportAggregate)
