from pathlib import Path

from varats.report.report import ReportAggregate, KeyedReportAggregate
from varats.report.tef_report import TEFReport


class WorkloadFeatureIntensityReport(
    KeyedReportAggregate[str, TEFReport], shorthand="FI-AGG", file_type="zip"
):
    """Report that aggregates the feature intensities for different binaries and
    workloads."""

    def __init__(self, path: Path):
        # TODO: Add key func per binary
        def key_func(file: Path) -> str:
            if file.is_dir():
                return file.name

            raise ValueError(f"Expected a directory, got {file}")

        super().__init__(path, TEFReport, key_func=key_func)

        for binary_folder in Path(self.__tmpdir.name).iterdir():
            if not binary_folder.is_dir():
                continue

            binary_name = binary_folder.name

            for file in binary_folder.iterdir():
                if file.suffix == ".json":
                    self.__reports[binary_name].append(TEFReport(file))
