"""Utility functions for handling filesystem related tasks."""

import typing as tp
from pathlib import Path


class FolderAlreadyPresentError(Exception):
    """Exception raised if an operation could not be performed because a folder
    was already present, e.g., when creating folders with a script."""

    def __init__(self, folder: tp.Union[Path, str]) -> None:
        super().__init__(
            f"Folder: '{str(folder)}' should be created "
            "but was already present."
        )
