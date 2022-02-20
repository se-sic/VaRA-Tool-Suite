"""Auto discover all tables."""

import importlib
import pkgutil


def discover() -> None:
    """Auto import all tables."""
    __all__ = []
    for _, module_name, _ in pkgutil.walk_packages(
        __path__, prefix="varats.tables."
    ):
        __all__.append(module_name)
        _module = importlib.import_module(module_name)
        globals()[module_name] = _module
