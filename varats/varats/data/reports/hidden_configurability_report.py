from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yaml

from varats.report.report import BaseReport


@dataclass
class HiddenConfigurabilityPoint:
    """Data class to store hidden configurability points."""
    filename: str
    line: int
    column: int
    var_type: str
    var_name: str


def from_dict(data: dict) -> HiddenConfigurabilityPoint:
    """Converts a dictionary to a HiddenConfigurabilityPoint object."""
    return HiddenConfigurabilityPoint(
        filename=data["Filename"],
        line=data["Lineno"],
        column=data["Colno"],
        var_type=data["Type"],
        var_name=data["VarName"]
    )


class HiddenConfigurabilityReport(BaseReport, shorthand="HC", file_type="yaml"):
    """Report class to store hidden configurability points."""

    def __init__(self, path: Path):
        super().__init__(path)
        self.__hidden_configurability_points = {}

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
        for hidden_var_kind in self.__hidden_configurability_points:
            type_count[hidden_var_kind] = len(
                self.__hidden_configurability_points[hidden_var_kind]
            )

        return type_count

    def get_num_configurability_points(self) -> int:
        """Returns the total number of hidden configurability points."""
        return sum(
            len(points)
            for points in self.__hidden_configurability_points.values()
        )
