"""
TODO: write me and update docs
"""

import typing as tp

FunctionType = tp.TypeVar("FunctionType")


def static_vars(**kwargs) -> tp.Any:
    """
    Decorates a function with static variables, passed with kwargs.

    @static_vars(var_name=value)
    def func(...):
    """

    def add_static_vars(func: FunctionType) -> FunctionType:
        for key in kwargs:
            setattr(func, key, kwargs[key])

        return func

    return add_static_vars
