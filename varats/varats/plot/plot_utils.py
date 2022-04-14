"""Plot module for util functionality."""

import typing as tp
from pathlib import Path

import pandas as pd
from matplotlib.axes import Axes

from varats.mapping.commit_map import CommitMap
from varats.utils.git_util import FullCommitHash, ShortCommitHash


def find_missing_revisions(
    data: tp.Iterable[tp.Tuple[tp.Any, pd.Series]], git_path: Path,
    cmap: CommitMap, should_insert_revision: tp.Callable[[tp.Any, tp.Any],
                                                         tp.Tuple[bool, float]],
    to_commit_hash: tp.Callable[[tp.Any], ShortCommitHash],
    are_neighbours: tp.Callable[[ShortCommitHash, ShortCommitHash], bool]
) -> tp.Set[FullCommitHash]:
    """Calculate a set of revisions that could be missing because the changes
    between certain points are to steep."""
    new_revs: tp.Set[FullCommitHash] = set()

    _, last_row = next(data)
    for _, row in data:
        should_insert, gradient = should_insert_revision(last_row, row)
        if should_insert:
            lhs_cm = to_commit_hash(last_row)
            rhs_cm = to_commit_hash(row)

            if are_neighbours(lhs_cm, rhs_cm):
                print(
                    "Found steep gradient between neighbours " +
                    f"{lhs_cm} - {rhs_cm}: {round(gradient, 5)}"
                )
                print(f"Investigate: git -C {git_path} diff {lhs_cm} {rhs_cm}")
            else:
                print(
                    "Unusual gradient between " +
                    f"{lhs_cm} - {rhs_cm}: {round(gradient, 5)}"
                )
                new_rev_id = round(
                    (cmap.short_time_id(lhs_cm) + cmap.short_time_id(rhs_cm)) /
                    2.0
                )
                new_rev = cmap.c_hash(new_rev_id)
                print(f"-> Adding {new_rev} as new revision to the sample set")
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
