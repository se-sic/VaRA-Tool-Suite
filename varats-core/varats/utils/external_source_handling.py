"""
Module for handling external varats sources.

This module provides loading facilities for loading custom user
projects/experiments/etc. into the varats ecosystem.
"""

import importlib
import logging
import pkgutil
import sys
import typing as tp
from pathlib import Path

LOG = logging.getLogger(__name__)


def determine_project_source_root(project_folder: Path) -> Path:
    return project_folder / project_folder.name


def relative_module_folder(project_folder: Path, module_folder: Path) -> Path:
    return module_folder.absolute().relative_to(project_folder.absolute())


def convert_path_to_module_path(path: Path) -> str:
    return str(path).replace('/', '.')


def load_python_modules_from_external_project(
    project_folder: Path,
    module_folder: Path,
    export_context: tp.Optional[tp.List[tp.Any]] = None
) -> None:
    """
    Load additional python modules from a external project.

    Args:
        project_folder: of the project we want to load from
        module_folder: that we want to load
        export_context: into which we want to export our modules (e.g., __all__)
    """
    if str(project_folder) not in sys.path:
        sys.path.insert(1, str(project_folder))

    relative_mf = relative_module_folder(
        project_folder=project_folder, module_folder=module_folder
    )
    module_prefix = f"{convert_path_to_module_path(relative_mf)}."

    for _, module_name, _ in pkgutil.walk_packages([str(module_folder)],
                                                   module_prefix):
        if export_context:
            export_context.append(module_name)

        _module = importlib.import_module(module_name)
        globals()[module_name] = _module
