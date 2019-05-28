"""
DataManager module handles the loading, creation, and caching of data classes.
"""
import hashlib
import os

from threading import Lock

from PyQt5.QtCore import QRunnable, QThreadPool, QObject, pyqtSlot, pyqtSignal


def sha256_checksum(file_path, block_size=65536):
    """
    Compute sha256 checksum of file.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as file_h:
        for block in iter(lambda: file_h.read(block_size), b''):
            sha256.update(block)
    return sha256.hexdigest()


class FileBlob(object):
    """
    A FileBlob is everything that is loaded from a file an converted to a
    VaRA DataClass.
    """
    def __init__(self, key, file_path, data):
        self.__key = key
        self.__file_path = file_path
        self.__class_object = data

    @property
    def key(self):
        """The key used as an index to the blob."""
        return self.__key

    @property
    def file_path(self):
        """File path to the loaded file."""
        return self.__file_path

    @property
    def data(self):
        """The loaded DataClass from the file."""
        return self.__class_object


class FileSignal(QObject):
    """
    Emit singlas after the file was loaded.
    """
    finished = pyqtSignal(object)
    clean = pyqtSignal()


class FileLoader(QRunnable):
    """
    Manages concurrent file loading.
    """
    def __init__(self, func, file_path, class_type):
        super(FileLoader, self).__init__()
        self.func = func
        self.file_path = file_path
        self.class_type = class_type
        self.signal = FileSignal()

    @pyqtSlot()
    def run(self):
        """
        Run the file loading method.
        """
        loaded_data_class = self.func(self.file_path, self.class_type)
        self.signal.finished.emit(loaded_data_class)
        self.signal.clean.emit()


class DataManager(object):
    """
    Manages data over the lifetime of the tools suite. The DataManager handles
    file loading, creation of DataClasses and caching of loaded files.
    """
    def __init__(self):
        self.file_map = dict()
        self.thread_pool = QThreadPool()
        self.loader_lock = Lock()

    def __load_data_class(self, file_path, DataClassTy):\
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

    def load_data_class(self, file_path, DataClassTy,
                        loaded_callback):        \
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

    def load_data_class_sync(self, file_path, DataClassTy):\
            # pylint: disable=invalid-name

        """
        Load a DataClass of type <DataClassTy> from a file synchronosly.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError

        loaded_file = self.__load_data_class(file_path, DataClassTy)
        self._release_lock()
        return loaded_file

    def _release_lock(self):
        self.loader_lock.release()


VDM = DataManager()
