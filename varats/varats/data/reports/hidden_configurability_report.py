import typing as tp
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from varats.report.gnu_time_report import WLTimeReportAggregate
from varats.report.multi_patch_report import MultiPatchReport
from varats.report.report import BaseReport, ReportAggregate


@dataclass
class CodeLocation:
    """Data class to store code locations."""
    filename: str
    line: int
    column: int


@dataclass
class HiddenConfigurabilityPoint:
    """Data class to store hidden configurability points."""
    declaration: CodeLocation
    uses: list[CodeLocation]
    tags: list[str] = field(default_factory=list)


def from_dict(data: dict) -> HiddenConfigurabilityPoint:
    """Converts a dictionary to a HiddenConfigurabilityPoint object."""
    location = data.get("Location")
    return HiddenConfigurabilityPoint(
        declaration=CodeLocation(
            filename=location["Filename"],
            line=location["Lineno"],
            column=location["Colno"]
        ),
        uses=[
            CodeLocation(
                filename=use["Filename"],
                line=use["Lineno"],
                column=use["Colno"]
            ) for use in data.get("UseLocations", [])
        ]
    )


class HiddenConfigurabilityReport(BaseReport, shorthand="HC", file_type="yaml"):
    """Report class to store hidden configurability points."""

    def __init__(self, path: Path):
        super().__init__(path)
        self.__hidden_configurability_points: tp.Dict[
            str, tp.Iterable[HiddenConfigurabilityPoint]] = {}

        with open(path, "r") as file:
            data = yaml.safe_load(file)

        for hidden_var_kind in data:
            self.__hidden_configurability_points[hidden_var_kind] = [
                from_dict(point) for point in data[hidden_var_kind]
            ]

    def get_hidden_configurability_points(self) -> dict:
        """Returns all hidden configurability points."""
        return self.__hidden_configurability_points

    def get_num_configurability_points_by_kind(self) -> dict:
        """Returns the number of hidden configurability points by kind."""
        type_count = {}
        for hidden_var_kind, values in self.__hidden_configurability_points.items(
        ):
            type_count[hidden_var_kind] = len(values)

        return type_count

    def get_num_configurability_points(self) -> int:
        """Returns the total number of hidden configurability points."""
        return sum(
            len(points)
            for points in self.__hidden_configurability_points.values()
        )


class MPRTimeWLAggregate(
    MultiPatchReport,
    shorthand="MPR" + WLTimeReportAggregate.shorthand(),
    file_type=ReportAggregate.FILE_TYPE
):
    """Aggregate for MultiPatchReports that contain WLTimeReports."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, WLTimeReportAggregate)
