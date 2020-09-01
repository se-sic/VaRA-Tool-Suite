"""Auto discover all plots."""

import importlib
import pkgutil

# avoid a potential cyclic import problem
import varats.plots.plot


def discover() -> None:
    """Auto import all plots."""
    __all__ = []
    for _, module_name, _ in pkgutil.walk_packages(
        __path__,  # type: ignore
        prefix="varats.plots."
    ):
        __all__.append(module_name)
        _module = importlib.import_module(module_name)
        globals()[module_name] = _module
