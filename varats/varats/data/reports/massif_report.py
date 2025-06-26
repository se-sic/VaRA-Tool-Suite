from pathlib import Path

import pandas as pd

from varats.report.report import BaseReport, ReportAggregate


class MassIfReport(BaseReport, shorthand="MIF", file_type="massif"):
    """Report for massif reports."""

    def _parse_massif_report(self, path: Path) -> pd.DataFrame:
        """Parse a massif report and return a pandas DataFrame."""
        with open(path, "r") as file:
            lines = file.readlines()

        data = {}
        current_time = None
        current_snapshot = {}

        for line in lines:
            line = line.strip()
            if line.startswith("snapshot="):
                # Save the previous snapshot data if it exists
                if current_time is not None:
                    data[current_time] = current_snapshot
                # Reset for the new snapshot
                current_snapshot = {}
                current_time = None
            elif line.startswith("time="):
                current_time = float(line.split("=")[1])
            elif line.startswith("mem_"):
                key, value = line.split("=")
                current_snapshot[key] = int(value)

        # Save the last snapshot data
        if current_time is not None:
            data[current_time] = current_snapshot

        # Convert the dictionary to a DataFrame
        df = pd.DataFrame.from_dict(data, orient="index")
        df.reset_index(
            inplace=True
        )  # Move the index (timestamp) into a column named "time"
        df.rename(
            columns={"index": "time"}, inplace=True
        )  # Ensure the column is named "time"
        return df

    def __init__(self, path: Path):
        super().__init__(path)
        self.__df = self._parse_massif_report(path)

    @property
    def data(self) -> pd.DataFrame:
        """Return the parsed data."""
        return self.__df


class MassIfAggregate(
    ReportAggregate[MassIfReport],
    shorthand=MassIfReport.SHORTHAND + ReportAggregate.SHORTHAND,
    file_type=ReportAggregate.FILE_TYPE
):
    """Context Manager for parsing multiple Perf Stat reports stored inside a
    zip file."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, MassIfReport)
