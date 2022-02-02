"""Auto discover all BenchBuild projects in subfolders."""

import importlib
import pkgutil


def discover() -> None:
    """Auto import all BenchBuild projects."""
    __all__ = []
    for _, module_name, _ in pkgutil.walk_packages(
        __path__, "varats.projects."
    ):
        __all__.append(module_name)
        _module = importlib.import_module(module_name)
        globals()[module_name] = _module
