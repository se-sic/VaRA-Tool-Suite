"""Auto discover all plots."""

import importlib
import pkgutil


def discover() -> None:
    """Auto import all plots."""
    __all__ = []
    for _, module_name, _ in pkgutil.walk_packages(
        __path__, prefix="varats.plots."
    ):
        __all__.append(module_name)
        _module = importlib.import_module(module_name)
        globals()[module_name] = _module
