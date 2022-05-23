"""Auto discover all reports in subfolders."""

import importlib
import pkgutil


def discover() -> None:
    """Auto import all varats reports."""
    __all__ = []
    for _, module_name, _ in pkgutil.walk_packages(
        __path__, 'varats.data.reports.'
    ):
        __all__.append(module_name)
        _module = importlib.import_module(module_name)
        globals()[module_name] = _module
