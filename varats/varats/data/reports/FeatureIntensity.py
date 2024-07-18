import typing as tp
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from varats.report.report import BaseReport
from varats.report.tef_report import TEFReport


class WorkloadFeatureIntensityReport(
    BaseReport, shorthand="WFIR", file_type="zip"
):
    """Report that aggregates the feature intensities for different binaries and
    workloads."""

    def __init__(self, path: Path):
        super().__init__(path)

        self.__reports: tp.Dict[str, tp.List[TEFReport]] = defaultdict(list)

        # Unpack zip file to temporary directory
        with ZipFile(path, "r") as archive:
            for name in archive.namelist():
                # Ignore directories
                if name.endswith("/"):
                    continue

                # Extract binary name from file name
                binary_name = name.split("/")[0]

                # Extract file to temporary directory and create report
                with TemporaryDirectory() as tmpdir:
                    archive.extract(name, tmpdir)
                    self.__reports[binary_name].append(
                        TEFReport(Path(tmpdir) / name)
                    )

    def binaries(self) -> tp.List[str]:
        return list(self.__reports.keys())

    def workloads_for_binary(self, binary: str) -> tp.List[str]:
        # Extract workloads from report file names
        # Report filenames are in format "feature_intensity_<workload>_0.json"
        return [
            report.filename.filename.split("_")[2]
            for report in self.__reports[binary]
        ]
