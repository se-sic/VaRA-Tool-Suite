"""Small helper methods that implement common functionalities."""

import typing as tp
from itertools import tee

FunctionType = tp.TypeVar("FunctionType")


def static_vars(**kwargs) -> tp.Any:
    """
    Decorates a function with static variables, passed with kwargs.

    For example::

        @static_vars(var_name=value)
        def func(...):
    """

    def add_static_vars(func: FunctionType) -> FunctionType:
        for key in kwargs:  # pylint: disable=consider-using-dict-items
            setattr(func, key, kwargs[key])

        return func

    return add_static_vars


T = tp.TypeVar('T')


# Forward port of itertools.pairwise
def pairwise(iterable: tp.Iterable[T]) -> tp.Iterable[tp.Tuple[T, T]]:
    first_iter, second_iter = tee(iterable)
    next(second_iter, None)
    return zip(first_iter, second_iter)
