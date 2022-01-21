"""Report moduel for phasar incremental analysis reports."""
import os
import shutil
import tempfile
import typing as tp
from pathlib import Path

from varats.report.report import BaseReport, FileStatusExtension, ReportFilename


class IncrementalReport(BaseReport, shorthand="Inc", file_type="zip"):
    """Report for phasar incremental analysis results."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        with tempfile.TemporaryDirectory() as tmp_result_dir:
            shutil.unpack_archive(path, extract_dir=Path(tmp_result_dir))

            # TODO: impl actual file handling
            collected_files = []
            for (dirpath, dirnames, filenames) in os.walk(Path(tmp_result_dir)):
                collected_files.extend(filenames)
                break

            print(f"Found files: {collected_files}")
