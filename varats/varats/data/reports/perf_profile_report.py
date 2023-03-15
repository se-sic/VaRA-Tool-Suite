"""Reports for perf profiling output."""

from pathlib import Path

from varats.report.report import BaseReport, ReportAggregate


class PerfProfileReport(BaseReport, shorthand="PERF", file_type="data"):
    """
    Binary `perf.data` file created by `perf record`.

    Can be converted into human-readable format via `perf data convert --to-json
    <out_filename>`.
    """


class PerfProfileReportAggregate(
    ReportAggregate[PerfProfileReport],
    shorthand=PerfProfileReport.SHORTHAND + ReportAggregate.SHORTHAND,
    file_type=ReportAggregate.FILE_TYPE
):
    """Context Manager for parsing multiple perf profile reports stored inside a
    zip file."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, PerfProfileReport)
