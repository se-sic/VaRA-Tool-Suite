import shutil
import typing as tp
from pathlib import Path
from types import TracebackType
from varats.experiment.experiment_util import ZippedReportFolder
from varats.report.report import BaseReport

class ReportAggregate(BaseReport, shorthand="Agg", file_type="zip"):
    """
    Context Manager for aggregating multiple reports in a zip file. An
    experiment step can simply put multiple reports into `tempdir`, which will
    be zipped upon `__exit()`. Existing files are extracted into `tempdir` on
    `__enter()`.
    """

    def __init__(self, path: Path, report_type: tp.Type[BaseReport]) -> None:
        super().__init__(path)
        self.__report_type = report_type
        self.__zipped_report = ZippedReportFolder(path)

    def __enter__(self) -> Path:
        """If the archive already exists, unzips the contents into `tempdir`."""
        self.__zipped_report.__enter__()

        zipfile = self.__zipped_report.zipfile
        print("a")
        if zipfile.exists():
            shutil.unpack_archive(zipfile, self.tempdir)

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
        """Returns the path to the temporary directory to drop files into."""
        return Path(self.__zipped_report.name)

    @property
    def report_type(self) -> tp.Type[BaseReport]:
        return self.__report_type

    @property
    def reports(self) -> list[BaseReport]:
        """Returns all reports present inside the folder."""
        return [self.__report_type(file) for file in self.tempdir.iterdir()]
