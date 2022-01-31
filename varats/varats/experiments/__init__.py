"""Auto discover all experiments in subfolders."""

import importlib
import pkgutil


def discover() -> None:
    """Auto import all BenchBuild experiments."""
    __all__ = []
    for _, module_name, _ in pkgutil.walk_packages(
        __path__, 'varats.experiments.'
    ):
        __all__.append(module_name)
        _module = importlib.import_module(module_name)
        globals()[module_name] = _module
