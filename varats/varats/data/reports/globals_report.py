"""Report moduel for phasar global analysis reports."""
import json
import typing as tp
from pathlib import Path

import numpy as np

from varats.report.report import BaseReport, FileStatusExtension, ReportFilename


class TimeMeasure():
    """Small time wrapper class to aggregate GlobalsReport measured time
    data.."""

    def __init__(self, mean: float, stddev: float) -> None:
        self.__mean = mean
        self.__stddev = stddev

    @property
    def mean(self) -> float:
        return self.__mean

    @property
    def stddev(self) -> float:
        return self.__stddev


class GlobalsReport():
    """Base class for phasar analysis reports to compare global analysis
    impact."""

    def __init__(self, path: Path):
        run_blobs: tp.List[str] = []
        with open(path, 'r') as report_file:
            tmp_blob: str = ""
            for line in report_file.readlines():
                if line.startswith("----"):
                    run_blobs.append(tmp_blob)
                    tmp_blob = ""
                else:
                    tmp_blob += line

        self.__data_from_first = json.loads(run_blobs[0])
        del self.__data_from_first["runtime-in-seconds"]

        # Calculate timeings
        self._timings: tp.List[int] = []
        for run_blob in run_blobs:
            loaded_data = json.loads(run_blob)
            self._timings.append(int(loaded_data["runtime-in-seconds"]))

        self.__update_run_values()

    def __update_run_values(self) -> None:
        self.__runs = len(self._timings)
        self.__runtime = TimeMeasure(
            np.mean(self._timings), np.std(self._timings)
        )

    @property
    def num_analyzed_global_ctors(self) -> int:
        return int(self.__data_from_first["#analyzed-global-ctors"])

    @property
    def num_analyzed_global_dtors(self) -> int:
        return int(self.__data_from_first["#analyzed-global-dtors"])

    @property
    def num_global_distrinct_types(self) -> int:
        return int(self.__data_from_first["#global-distinct-types"])

    @property
    def num_global_int_typed(self) -> int:
        return int(self.__data_from_first["#global-int-typed"])

    @property
    def num_global_uses(self) -> int:
        return int(self.__data_from_first["#global-uses"])

    @property
    def num_global_vars(self) -> int:
        return int(self.__data_from_first["#global-vars"])

    @property
    def num_globals(self) -> int:
        return int(self.__data_from_first["#globals"])

    @property
    def num_non_top_vals_at_end(self) -> int:
        return int(self.__data_from_first["#non-top-vals-at-end"])

    @property
    def num_non_top_vals_at_start(self) -> int:
        return int(self.__data_from_first["#non-top-vals-at-start"])

    @property
    def num_required_globals_generation(self) -> int:
        return int(self.__data_from_first["#required-globals-generation"])

    @property
    def auto_globals(self) -> int:
        return int(self.__data_from_first["auto-globals"])

    @property
    def entry_points(self) -> str:
        return str(self.__data_from_first["entry-points"])

    @property
    def program(self) -> str:
        return str(self.__data_from_first["program"])

    @property
    def runs(self) -> int:
        return self.__runs

    @property
    def runtime_in_secs(self) -> TimeMeasure:
        return self.__runtime

    def extend_runs(self, other_report: 'GlobalsReport') -> None:
        """Add more runs to this report."""
        self._timings.extend(other_report._timings)
        self.__update_run_values()

    def __str__(self) -> str:
        output_data = dict(self.__data_from_first)
        output_data["mean time"] = f"{self.runtime_in_secs.mean} " +\
            f"(+/- {self.runtime_in_secs.stddev:.2f})"
        return json.dumps(output_data, indent=4)


class GlobalsReportWithout(GlobalsReport, BaseReport):
    """Report for phasar analysis results without new globals support."""

    SHORTHAND = "GRWithout"
    FILE_TYPE = "json"

    @classmethod
    def shorthand(cls) -> str:
        """Shorthand for this report."""
        return cls.SHORTHAND

    @staticmethod
    def get_file_name(
        project_name: str,
        binary_name: str,
        project_version: str,
        project_uuid: str,
        extension_type: FileStatusExtension,
        file_ext: str = ".txt"
    ) -> str:
        """
        Generates a filename for a report file.

        Args:
            project_name: name of the project for which the report was generated
            binary_name: name of the binary for which the report was generated
            project_version: version of the analyzed project, i.e., commit hash
            project_uuid: benchbuild uuid for the experiment run
            extension_type: to specify the status of the generated report
            file_ext: file extension of the report file

        Returns:
            name for the report file that can later be uniquly identified
        """
        return ReportFilename.get_file_name(
            GlobalsReportWithout.SHORTHAND, project_name, binary_name,
            project_version, project_uuid, extension_type,
            GlobalsReportWithout.FILE_TYPE
        )


class GlobalsReportWith(GlobalsReport, BaseReport):
    """Report for phasar analysis results with new globals support."""

    SHORTHAND = "GRWith"
    FILE_TYPE = "json"

    @classmethod
    def shorthand(cls) -> str:
        """Shorthand for this report."""
        return cls.SHORTHAND

    @staticmethod
    def get_file_name(
        project_name: str,
        binary_name: str,
        project_version: str,
        project_uuid: str,
        extension_type: FileStatusExtension,
        file_ext: str = ".txt"
    ) -> str:
        """
        Generates a filename for a report file.

        Args:
            project_name: name of the project for which the report was generated
            binary_name: name of the binary for which the report was generated
            project_version: version of the analyzed project, i.e., commit hash
            project_uuid: benchbuild uuid for the experiment run
            extension_type: to specify the status of the generated report
            file_ext: file extension of the report file

        Returns:
            name for the report file that can later be uniquly identified
        """
        return ReportFilename.get_file_name(
            GlobalsReportWith.SHORTHAND, project_name, binary_name,
            project_version, project_uuid, extension_type,
            GlobalsReportWith.FILE_TYPE
        )
