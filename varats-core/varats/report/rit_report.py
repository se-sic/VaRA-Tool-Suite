"""Report module to create and handle region interaction performance reports."""

import json
import re
import typing as tp
from enum import Enum
from pathlib import Path

from varats.experiment.workload_util import WorkloadSpecificReportAggregate
from varats.report.report import BaseReport, ReportAggregate


class RegionInteractionEntry:
    """Represents a region interaction entry that was captured during the
    analysis of a target program."""

    def __init__(self, interaction: str, time: int) -> None:
        self.__interaction = interaction
        self.__time = time

    @property
    def interaction(self) -> str:
        return self.__interaction

    @property
    def time(self) -> int:
        return self.__time

    def __str__(self) -> str:
        return f"""{{
    interaction: {self.interaction}
    time: {self.time}
}}
"""

    def __repr__(self) -> str:
        return str(self)


class RITReport(BaseReport, shorthand="RIT", file_type="json"):
    """Report class to access region interaction report format files."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)

        with open(self.path, "r", encoding="utf-8") as json_rit_report:
            data = json.load(json_rit_report)
            self.__timestamp_unit = str(data["timestampUnit"])
            self.__region_interaction_entries = self._parse_region_interaction_entries(
                data["regionTimes"]
            )

    @property
    def timestamp_unit(self) -> str:
        return self.__timestamp_unit

    @property
    def region_interaction_entries(self) -> tp.List[RegionInteractionEntry]:
        return self.__region_interaction_entries

    @staticmethod
    def _parse_region_interaction_entries(entry_dict: tp.Dict[str, str]):
        region_interaction_entries: tp.List[RegionInteractionEntry] = []
        for interaction, time in entry_dict.items():
            region_interaction_entries.append(
                RegionInteractionEntry(interaction, int(time))
            )
        return region_interaction_entries


class RITReportAggregate(
    ReportAggregate[RITReport],
    shorthand=RITReport.SHORTHAND + ReportAggregate.SHORTHAND,
    file_type=ReportAggregate.FILE_TYPE
):
    """Context Manager for parsing multiple RIT reports stored inside a zip
    file."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, RITReport)


__WORKLOAD_FILE_REGEX = re.compile(r"trace\_(?P<label>.+)$")


def get_workload_label(workload_specific_report_file: Path) -> tp.Optional[str]:
    match = __WORKLOAD_FILE_REGEX.search(workload_specific_report_file.stem)
    if match:
        return str(match.group("label"))

    return None


class WorkloadSpecificRITReportAggregate(
    WorkloadSpecificReportAggregate[RITReport], shorthand="", file_type=""
):

    def __init__(self, path: Path) -> None:
        super().__init__(
            path,
            RITReport,
            get_workload_label,
        )
