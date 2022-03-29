"""Simple report module to aggregate multiple reports into a single file."""

import shutil
import typing as tp
from pathlib import Path
from types import TracebackType
from typing import TypeVar, Generic

from varats.experiment.experiment_util import ZippedReportFolder
from varats.report.report import BaseReport


T = TypeVar('T', bound=BaseReport)

class ReportAggregate(BaseReport, Generic[T], shorthand="Agg", file_type="zip"):
    """
    Context Manager for aggregating multiple reports in a zip file.
    
    An experiment step can simply put multiple reports into `tempdir`, which
    will be zipped upon `__exit()`. Existing files are extracted into `tempdir`
    on `__enter()`. `__enter()` must be called before accessing any properties
    of this class.
    """

    def __init__(self, path: Path, report_type: tp.Type[T]) -> None:
        super().__init__(path.with_suffix(".zip"))
        self.__zipped_report = ZippedReportFolder(self.path)
        self.__report_type = report_type

    def __enter__(self) -> Path:
        """Creates the temporary directory and unzips reports from an existing
        zip archive into it."""
        self.__zipped_report.__enter__()

        if self.path.exists():
            shutil.unpack_archive(self.path, self.tempdir)

        return self.tempdir

    def __exit__(
        self, exc_type: tp.Optional[tp.Type[BaseException]],
        exc_value: tp.Optional[BaseException],
        exc_traceback: tp.Optional[TracebackType]
    ) -> None:
        """Zips contents in `tempdir`."""
        self.__zipped_report.__exit__(exc_type, exc_value, exc_traceback)

    @property
    def tempdir(self) -> Path:
        """Returns the path to the temporary directory to drop reports into."""
        return Path(self.__zipped_report.name)

    @property
    def reports(self) -> tp.List[T]:
        """Returns a list of all reports present inside `tempdir`."""
        return [self.__report_type(file) for file in self.tempdir.iterdir()]
