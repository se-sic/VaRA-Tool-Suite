"""Auto discover all tables."""

import pkgutil

# avoid a potential cyclic import problem
import varats.tables.table


def discover() -> None:
    """Auto import all tables."""
    __all__ = []
    for loader, module_name, _ in pkgutil.walk_packages(
        __path__  # type: ignore
    ):
        __all__.append(module_name)
        _module = loader.find_module(module_name).load_module(module_name)
        globals()[module_name] = _module
