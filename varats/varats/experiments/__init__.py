"""Auto discover all experiments in subfolders."""

import importlib
import pkgutil
from pathlib import Path

import varats.utils.external_source_handling as esh
from varats.utils.settings import vara_cfg


def discover() -> None:
    """Auto import all BenchBuild experiments."""

    __all__ = []

    for _, module_name, _ in pkgutil.walk_packages(
        __path__, 'varats.experiments.'
    ):
        __all__.append(module_name)
        _module = importlib.import_module(module_name)
        globals()[module_name] = _module

    extra_sources = vara_cfg()['external_source_repositories'].value
    for p in [Path(p) for p in extra_sources]:
        module_folder = p / "experiments"
        esh.load_python_modules_from_external_project(p, module_folder, __all__)
