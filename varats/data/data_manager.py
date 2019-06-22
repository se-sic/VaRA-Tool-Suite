"""
DataManager module handles the loading, creation, and caching of data classes.
"""

import typing as tp
import hashlib
import os
from pathlib import Path

from threading import Lock

from PyQt5.QtCore import QRunnable, QThreadPool, QObject, pyqtSlot, pyqtSignal

from varats.data.commit_report import CommitReport

# Add other loadable Types
# TODO: remove double CommitReport after adding second type
LoadableType = tp.TypeVar('LoadableType', CommitReport, CommitReport)


def sha256_checksum(file_path: Path, block_size: int = 65536) -> str:
    """
    Compute sha256 checksum of file.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as file_h:
        for block in iter(lambda: file_h.read(block_size), b''):
            sha256.update(block)
    return sha256.hexdigest()


class FileBlob():
    """
    A FileBlob is everything that is loaded from a file an converted to a
    VaRA DataClass.
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


class FileSignal(QObject):  # type: ignore
    """
    Emit singlas after the file was loaded.
    """
    finished = pyqtSignal(object)
    clean = pyqtSignal()


class FileLoader(QRunnable):   # type: ignore
    """
    Manages concurrent file loading.
    """

    def __init__(
            self,
            func: tp.Callable[[Path, tp.Type[LoadableType]], LoadableType],
            file_path: Path, class_type: tp.Type[LoadableType]) -> None:
        super(FileLoader, self).__init__()
        self.func = func
        self.file_path = file_path
        self.class_type = class_type
        self.signal = FileSignal()

    @pyqtSlot()  # type: ignore
    def run(self) -> None:
        """
        Run the file loading method.
        """
        loaded_data_class = self.func(self.file_path, self.class_type)
        self.signal.finished.emit(loaded_data_class)
        self.signal.clean.emit()


class DataManager():
    """
    Manages data over the lifetime of the tools suite. The DataManager handles
    file loading, creation of DataClasses and caching of loaded files.
    """

    def __init__(self) -> None:
        self.file_map: tp.Dict[str, FileBlob] = dict()
        self.thread_pool = QThreadPool()
        self.loader_lock = Lock()

    def __load_data_class(self, file_path: Path,
                          DataClassTy: tp.Type[LoadableType]) -> LoadableType:
        # pylint: disable=invalid-name
        """
        Load a DataClass of type <DataClassTy> from a file.
        """
        self.loader_lock.acquire()

        key = sha256_checksum(file_path)
        if key in self.file_map:
            return self.file_map[key].data

        try:
            new_blob = FileBlob(key, file_path, DataClassTy(file_path))
        except Exception as e:
            self.loader_lock.release()
            raise e
        self.file_map[key] = new_blob

        return new_blob.data

    def load_data_class(
            self, file_path: Path, DataClassTy: tp.Type[LoadableType],
            loaded_callback: tp.Callable[[LoadableType], None]) -> None:
        # pylint: disable=invalid-name
        """
        Load a DataClass of type <DataClassTy> from a file asynchronosly.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError

        worker = FileLoader(self.__load_data_class, file_path, DataClassTy)
        worker.signal.finished.connect(loaded_callback)
        worker.signal.clean.connect(self._release_lock)
        self.thread_pool.start(worker)

    def load_data_class_sync(
            self, file_path: Path,
            DataClassTy: tp.Type[LoadableType]) -> LoadableType:
        # pylint: disable=invalid-name
        """
        Load a DataClass of type <DataClassTy> from a file synchronosly.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError

        loaded_file = self.__load_data_class(file_path, DataClassTy)
        self._release_lock()
        return loaded_file

    def _release_lock(self) -> None:
        self.loader_lock.release()


VDM = DataManager()
