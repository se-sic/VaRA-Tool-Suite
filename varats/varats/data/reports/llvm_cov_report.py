import json
import typing as tp
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from plumbum import local

from varats.report.report import BaseReport, ReportFilename


@dataclass
class CodeRegion:
    """Class representing a code region in the coverage report."""

    def __init__(self, start: int, end: int) -> None:
        self.__start = start
        self.__end = end

    @property
    def start(self) -> int:
        """Return the start of the code region."""
        return self.__start

    @property
    def end(self) -> int:
        """Return the end of the code region."""
        return self.__end

    def contains(self, line: int) -> bool:
        """Check if the given line is in the code region."""
        return self.__start <= line < self.__end

    def __and__(self, other: "CodeRegion") -> "CodeRegion":
        """Returns the overlap of two code regions if it exists."""
        if self.contains(other.start) or self.contains(other.end):
            return CodeRegion(
                max(self.start, other.start), min(self.end, other.end)
            )

        return CodeRegion(1, 0)  # Empty region

    def __or__(self, other: "CodeRegion") -> "CodeRegion":
        """Returns the union of two code regions if it exists."""
        if self.contains(other.start) or self.contains(other.end):
            return CodeRegion(
                min(self.start, other.start), max(self.end, other.end)
            )

        return CodeRegion(1, 0)


class LLVMCoverageReport(BaseReport, shorthand="LCOV", file_type="json"):
    """LLVM coverage report."""

    NAME = "LLVM_Coverage_Report"
    DESCRIPTION = "LLVM coverage report"

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        with open(path, "r") as file:
            self.coverage_data = json.load(file)

        # Convert tuples to CodeRegion objects
        for file, regions in self.coverage_data.items():
            self.coverage_data[file] = [
                CodeRegion(start, end) for start, end in regions
            ]


class LLVMProfDataReport(BaseReport, shorthand="LPD", file_type="profdata"):
    """Report for raw LLVM profiles."""

    NAME = "LLVM_ProfData"
    DESCRIPTION = "LLVM raw profile data report"

    def __init__(self, path: Path) -> None:
        super().__init__(path)
