"""Report module to create and handle region interaction performance reports."""

import json
import re
import typing as tp
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


class PerfInfluenceTraceReport(BaseReport, shorthand="PIT", file_type="json"):
    """Report class to access region interaction report format files."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)

        with open(self.path, "r", encoding="utf-8") as json_rit_report:
            data = json.load(json_rit_report)
            self.__timestamp_unit = str(data["timestampUnit"])
            self.__region_interaction_entries = \
                self._parse_region_interaction_entries(data["regionTimes"])
            self.__region_name_map = self._parse_region_name_map(
                data["regionNames"]
            )

    @property
    def timestamp_unit(self) -> str:
        return self.__timestamp_unit

    @property
    def region_interaction_entries(self) -> tp.List[RegionInteractionEntry]:
        return self.__region_interaction_entries

    def __str__(self) -> str:
        stringify = f"Term = Value ({self.timestamp_unit})\n"
        stringify += "-" * len(stringify) + "\n"

        for entry in self.region_interaction_entries:
            interaction_name = self._translate_interaction(entry.interaction)
            stringify += f"{interaction_name} = {entry.time}\n"

        return stringify

    def _translate_interaction(self, interaction: str) -> str:
        sub_terms = interaction.split('*')
        return "*".join(
            map(
                lambda region_id: self.__region_name_map[int(region_id)],
                sub_terms
            )
        )

    @staticmethod
    def _parse_region_interaction_entries(
        entry_dict: tp.Dict[str, str]
    ) -> tp.List[RegionInteractionEntry]:
        region_interaction_entries: tp.List[RegionInteractionEntry] = []
        for interaction, time in entry_dict.items():
            region_interaction_entries.append(
                RegionInteractionEntry(interaction, int(time))
            )
        return region_interaction_entries

    @staticmethod
    def _parse_region_name_map(
        entry_dict: tp.Dict[str, str]
    ) -> tp.Dict[int, str]:
        mapped_region_names: tp.Dict[int, str] = {}

        for region_id, region_name in entry_dict.items():
            mapped_region_names[int(region_id)] = region_name

        return mapped_region_names


class PerfInfluenceTraceReportAggregate(
    ReportAggregate[PerfInfluenceTraceReport],
    shorthand=PerfInfluenceTraceReport.SHORTHAND + ReportAggregate.SHORTHAND,
    file_type=ReportAggregate.FILE_TYPE
):
    """Context Manager for parsing multiple RIT reports stored inside a zip
    file."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, PerfInfluenceTraceReport)


__WORKLOAD_FILE_REGEX = re.compile(r"trace\_(?P<label>.+)$")


def get_workload_label(workload_specific_report_file: Path) -> tp.Optional[str]:
    """Helper function to access workload labels for workload specific
    PITReports."""
    if (
        match :=
        __WORKLOAD_FILE_REGEX.search(workload_specific_report_file.stem)
    ):
        return str(match.group("label"))

    return None


class WorkloadSpecificPITReportAggregate(
    WorkloadSpecificReportAggregate[PerfInfluenceTraceReport],
    shorthand="",
    file_type=""
):
    """Workload specific adapter class to access region interaction reports."""

    def __init__(self, path: Path) -> None:
        super().__init__(
            path,
            PerfInfluenceTraceReport,
            get_workload_label,
        )
