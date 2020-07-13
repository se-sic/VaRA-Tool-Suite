"""Plot module for util functionality."""

import functools
import typing as tp
from pathlib import Path

from matplotlib.axes import Axes

from varats.data.reports.commit_report import CommitMap


def __check_required_args_impl(
    required_args: tp.List[str], kwargs: tp.Dict[str, tp.Any]
) -> None:
    """Implementation to check if all required graph args are passed by the
    user."""
    for arg in required_args:
        if arg not in kwargs:
            raise AssertionError(
                "Argument {} was not specified but is required for this graph.".
                format(arg)
            )


def check_required_args(
    required_args: tp.List[str]
) -> tp.Callable[[tp.Callable[..., tp.Any]], tp.Callable[..., tp.Any]]:
    """Check if all required graph args are passed by the user."""

    def decorator_pp(
        func: tp.Callable[..., tp.Any]
    ) -> tp.Callable[..., tp.Any]:

        @functools.wraps(func)
        def wrapper_func(*args: tp.Any, **kwargs: tp.Any) -> tp.Any:
            __check_required_args_impl(required_args, kwargs)
            return func(*args, **kwargs)

        return wrapper_func

    return decorator_pp


def find_missing_revisions(
    data: tp.Generator[tp.Any, None, None], git_path: Path, cmap: CommitMap,
    should_insert_revision: tp.Callable[[tp.Any, tp.Any], tp.Tuple[bool,
                                                                   float]],
    to_commit_hash: tp.Callable[[tp.Any],
                                str], are_neighbours: tp.Callable[[str, str],
                                                                  bool]
) -> tp.Set[str]:
    """Calculate a set of revisions that could be missing because the changes
    between certain points are to steep."""
    new_revs: tp.Set[str] = set()

    _, last_row = next(data)
    for _, row in data:
        should_insert, gradient = should_insert_revision(last_row, row)
        if should_insert:
            lhs_cm = to_commit_hash(last_row)
            rhs_cm = to_commit_hash(row)

            if are_neighbours(lhs_cm, rhs_cm):
                print(
                    "Found steep gradient between neighbours " +
                    "{lhs_cm} - {rhs_cm}: {gradient}".format(
                        lhs_cm=lhs_cm,
                        rhs_cm=rhs_cm,
                        gradient=round(gradient, 5)
                    )
                )
                print(
                    "Investigate: git -C {git_path} diff {lhs} {rhs}".format(
                        git_path=git_path, lhs=lhs_cm, rhs=rhs_cm
                    )
                )
            else:
                print(
                    "Unusual gradient between " +
                    "{lhs_cm} - {rhs_cm}: {gradient}".format(
                        lhs_cm=lhs_cm,
                        rhs_cm=rhs_cm,
                        gradient=round(gradient, 5)
                    )
                )
                new_rev_id = round(
                    (cmap.short_time_id(lhs_cm) + cmap.short_time_id(rhs_cm)) /
                    2.0
                )
                new_rev = cmap.c_hash(new_rev_id)
                print(
                    "-> Adding {rev} as new revision to the sample set".format(
                        rev=new_rev
                    )
                )
                new_revs.add(new_rev)
        last_row = row
    return new_revs


def pad_axes(
    ax: Axes,
    pad_x: tp.Optional[float] = None,
    pad_y: tp.Optional[float] = None
) -> None:
    """Add some padding to the axis limits."""
    if pad_x:
        x_min, x_max = ax.get_xlim()
        padding_x = (x_max - x_min) * pad_x
        ax.set_xlim(x_min - padding_x, x_max + padding_x)

    if pad_y:
        y_min, y_max = ax.get_ylim()
        padding_y = (y_max - y_min) * pad_y
        ax.set_ylim(y_min - padding_y, y_max + padding_y)


def align_yaxis(ax1: Axes, value1: float, ax2: Axes, value2: float) -> None:
    """
    Adjust ax2 ylimit so that value2 in ax2 is aligned to value1 in ax1.

    See https://stackoverflow.com/a/26456731
    """
    _, y_ax1 = ax1.transData.transform((0, value1))
    _, y_ax2 = ax2.transData.transform((0, value2))
    adjust_yaxis(ax2, (y_ax1 - y_ax2) / 2, value2)
    adjust_yaxis(ax1, (y_ax2 - y_ax1) / 2, value1)


def adjust_yaxis(ax: Axes, ydif: float, value: float) -> None:
    """
    Shift axis ax by ydiff, maintaining point value at the same location.

    See https://stackoverflow.com/a/26456731
    """
    inv = ax.transData.inverted()
    _, delta_y = inv.transform((0, 0)) - inv.transform((0, ydif))
    miny, maxy = ax.get_ylim()
    miny, maxy = miny - value, maxy - value
    if -miny > maxy or (-miny == maxy and delta_y > 0):
        nminy = miny
        nmaxy = miny * (maxy + delta_y) / (miny + delta_y)
    else:
        nmaxy = maxy
        nminy = maxy * (miny + delta_y) / (maxy + delta_y)
    ax.set_ylim(nminy + value, nmaxy + value)
