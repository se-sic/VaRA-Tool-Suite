"""Auto discover all tables."""

import importlib
import pkgutil

# avoid a potential cyclic import problem
import varats.tables.table


def discover() -> None:
    """Auto import all tables."""
    __all__ = []
    for _, module_name, _ in pkgutil.walk_packages(
        __path__,  # type: ignore
        "varats.tables."
    ):
        __all__.append(module_name)
        _module = importlib.import_module(module_name)
        globals()[module_name] = _module
