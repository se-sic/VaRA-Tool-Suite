"""
Hack to make pytest correctly handle namespace packages.

Adapted from https://stackoverflow.com/a/50175552
"""
import itertools
import pathlib

import _pytest.pathlib

resolve_pkg_path_orig = _pytest.pathlib.resolve_package_path

# we consider all dirs in repo/ to be namespace packages
rootdir = pathlib.Path(__file__).parent.resolve()
namespace_pkg_dirs = [
    rootdir / "varats-core/varats",
    rootdir / "varats/varats",
]


# patched method
def resolve_package_path(path):
    result = None
    for parent in itertools.chain((path,), path.parents):
        if parent.is_dir():
            if not parent.joinpath("__init__.py").is_file():
                if parent in namespace_pkg_dirs:
                    result = parent
                break
            if not parent.name.isidentifier():
                break
            result = parent
    return result


# apply patch
_pytest.pathlib.resolve_package_path = resolve_package_path
