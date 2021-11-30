"""Auto discover all core reports in subfolders."""

import importlib
import pkgutil


def discover() -> None:
    """Auto import all core varats reports."""
    __all__ = []
    for _, module_name, _ in pkgutil.walk_packages(
        __path__,  # type: ignore
        'varats.report.'
    ):
        __all__.append(module_name)
        _module = importlib.import_module(module_name)
        globals()[module_name] = _module
