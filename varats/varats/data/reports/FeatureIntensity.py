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

        self.__reports = defaultdict(list)

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
