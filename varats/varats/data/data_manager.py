"""
The DataManager module handles the loading, creation, and caching of data
classes.

With the DataManager in the background, we can load files from multiple
locations within the tool suite, without loading the same file twice. In
addition, this speeds up reloading of files, for example, in interactive plots,
like in jupyter notebooks, where we sometimes re-execute triggers a file load.
"""

import hashlib
import os
import typing as tp
from functools import partial
from multiprocessing import Pool
from pathlib import Path
from threading import Lock

from PyQt5.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot

from varats.report.report import BaseReport

LoadableType = tp.TypeVar('LoadableType', bound=BaseReport)


def sha256_checksum(file_path: Path, block_size: int = 65536) -> str:
    """
    Compute sha256 checksum of file.

    Args:
        file_path: path to the file
        block_size: amount of bytes read per cycle

    Returns:
        sha256 hash of the file
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as file_h:
        for block in iter(lambda: file_h.read(block_size), b''):
            sha256.update(block)
    sha256.update(bytes(file_path.name, 'utf-8'))
    return sha256.hexdigest()


class FileBlob():
    """
    A FileBlob is a keyed data blob for everything that is loadable from a file
    and can be converted to a VaRA DataClass.

    Args:
        key: identifier for the file
        file_path: path to the file
        data: a blob of data in memory
    """

    def __init__(self, key: str, file_path: Path, data: LoadableType) -> None:
        self.__key = key
        self.__file_path = file_path
        self.__class_object = data

    @property
    def key(self) -> str:
        """The key used as an index to the blob."""
        return self.__key

    @property
    def file_path(self) -> Path:
        """File path to the loaded file."""
        return self.__file_path

    @property
    def data(self) -> LoadableType:
        """The loaded DataClass from the file."""
        return self.__class_object


class FileSignal(QObject):
    """Emit signals after the file was loaded."""
    finished = pyqtSignal(object)
    clean = pyqtSignal()


class FileLoader(QRunnable):
    """Manages concurrent file loading in the background of the application."""

    def __init__(
        self, func: tp.Callable[[Path, tp.Type[LoadableType]], LoadableType],
        file_path: Path, class_type: tp.Type[LoadableType]
    ) -> None:
        super().__init__()
        self.func = func
        self.file_path = file_path
        self.class_type = class_type
        self.signal = FileSignal()

    @pyqtSlot()
    def run(self) -> None:
        """Run the file loading method."""
        loaded_data_class = self.func(self.file_path, self.class_type)
        self.signal.finished.emit(loaded_data_class)
        self.signal.clean.emit()


class DataManager():
    """
    Manages data over the lifetime of the tool suite.

    The DataManager handles the concurrent file loading, creation of DataClasses
    and caching of loaded files.
    """

    def __init__(self) -> None:
        self.file_map: tp.Dict[str, FileBlob] = {}
        self.thread_pool = QThreadPool()
        self.loader_lock = Lock()

    def __load_data_class(
        self, file_path: Path, DataClassTy: tp.Type[LoadableType]
    ) -> LoadableType:
        # pylint: disable=invalid-name
        """Load a DataClass of type <DataClassTy> from a file."""
        key = sha256_checksum(file_path)

        self.loader_lock.acquire()  # pylint: disable=consider-using-with
        if key in self.file_map:
            return tp.cast(LoadableType, self.file_map[key].data)

        self.loader_lock.release()

        try:
            new_blob = FileBlob(key, file_path, DataClassTy(file_path))
        except Exception as e:
            raise e

        self.loader_lock.acquire()  # pylint: disable=consider-using-with
        # unlocking in the happy path is performed by the loading function
        self.file_map[key] = new_blob

        return tp.cast(LoadableType, new_blob.data)

    def load_data_class(
        self, file_path: Path, DataClassTy: tp.Type[LoadableType],
        loaded_callback: tp.Callable[[LoadableType], None]
    ) -> None:
        # pylint: disable=invalid-name
        """
        Load a DataClass of type <DataClassTy> from a file asynchronosly.

        Args:
            file_path: to the file
            DataClassTy: type of the report class to be loaded
            loaded_callback: that gets called after loading has finished
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError

        worker = FileLoader(self.__load_data_class, file_path, DataClassTy)
        worker.signal.finished.connect(loaded_callback)
        worker.signal.clean.connect(self._release_lock)
        self.thread_pool.start(worker)

    def load_data_class_sync(
        self, file_path: Path, DataClassTy: tp.Type[LoadableType]
    ) -> LoadableType:
        # pylint: disable=invalid-name
        """
        Load a DataClass of type <DataClassTy> from a file synchronosly.

        Args:
            file_path: to the file
            DataClassTy: type of the report class to be loaded

        Returns:
            the loaded report file
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError

        loaded_file = self.__load_data_class(file_path, DataClassTy)
        self._release_lock()
        return loaded_file

    def clean_cache(self) -> None:
        with self.loader_lock:
            self.file_map.clear()

    def _release_lock(self) -> None:
        self.loader_lock.release()


def _load_data_class_pool(
    file_path: Path, report_type: tp.Type[LoadableType]
) -> LoadableType:
    return VDM.load_data_class_sync(file_path, report_type)


def load_multiple_reports(
    file_paths: tp.List[Path], report_type: tp.Type[BaseReport]
) -> tp.List[tp.Any]:
    """

    Args:
        file_paths: list of files to load
        report_type: type of the report class to be loaded

    Returns: a list of loaded reports
    """
    loaded_reports = []

    with Pool() as process_pool:
        loaded_reports = process_pool.map(
            partial(_load_data_class_pool, report_type=report_type), file_paths
        )

    return loaded_reports


VDM = DataManager()
