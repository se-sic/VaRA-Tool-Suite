"""Utility functions for handling filesystem related tasks."""
import fcntl
import os.path
import typing as tp
from contextlib import contextmanager
from pathlib import Path


class FolderAlreadyPresentError(Exception):
    """Exception raised if an operation could not be performed because a folder
    was already present, e.g., when creating folders with a script."""

    def __init__(self, folder: tp.Union[Path, str]) -> None:
        super().__init__(
            f"Folder: '{str(folder)}' should be created "
            "but was already present."
        )


@contextmanager
def lock_file(lock_path: Path,
              lock_mode: int = fcntl.LOCK_EX) -> tp.Generator[None, None, None]:
    # Create directories until lock file if required
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)

    open_mode = os.O_RDWR | os.O_CREAT | os.O_TRUNC
    lock_fd = os.open(lock_path, open_mode)
    try:
        fcntl.flock(lock_fd, lock_mode)
        yield
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
