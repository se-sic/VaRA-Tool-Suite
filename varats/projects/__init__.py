"""
Auto discover all BenchBuild projects in subfolders
"""

import pkgutil


def discover():
    """
    Auto import all BenchBuild projects.
    """
    __all__ = []
    for loader, module_name, _ in pkgutil.walk_packages(__path__):
        __all__.append(module_name)
        _module = loader.find_module(module_name).load_module(module_name)
        globals()[module_name] = _module
