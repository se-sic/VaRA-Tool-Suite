"""Module for yaml utility tools, e.g., storing and loading yamls from files."""
import errno
import os
import typing as tp
from pathlib import Path

import yaml


def store_as_yaml(file_path: Path, objects: tp.Iterable[tp.Any]) -> None:
    """
    Store objects in a yaml file.

    The objects that should be stored must implement a function get_dict()
    that returns a dict representation of the object.

    Args:
        file_path: The file to store the objects in.
        objects: The objects to store.
    """
    with open(file_path, "w") as yaml_file:
        yaml_file.write(
            yaml.dump_all([obj.get_dict() for obj in objects],
                          explicit_start=True,
                          explicit_end=True)
        )


def load_yaml(file_path: Path) -> tp.Iterator[tp.Any]:
    """
    Load a yaml file.
    Args:
        file_path: The file to load.

    Returns: A representation of the loaded yaml file.
    """
    if file_path.exists():
        with open(file_path, "r") as yaml_file:
            return list(yaml.load_all(yaml_file,
                                      Loader=yaml.CLoader)).__iter__()

    raise FileNotFoundError(
        errno.ENOENT, os.strerror(errno.ENOENT), str(file_path)
    )
