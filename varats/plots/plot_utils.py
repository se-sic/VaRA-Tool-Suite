"""
Plot module for util functionality.
"""

import typing as tp
import functools
from pathlib import Path

from varats.data.reports.commit_report import CommitMap


def __check_required_args_impl(required_args: tp.List[str],
                               kwargs: tp.Dict[str, tp.Any]) -> None:
    """
    Implementation to check if all required graph args are passed by the user.
    """
    for arg in required_args:
        if arg not in kwargs:
            raise AssertionError(
                "Argument {} was not specified but is required for this graph.".
                format(arg))


def check_required_args(
        required_args: tp.List[str]
) -> tp.Callable[[tp.Callable[..., tp.Any]], tp.Callable[..., tp.Any]]:
    """
    Check if all required graph args are passed by the user.
    """

    def decorator_pp(func: tp.Callable[..., tp.Any]
                    ) -> tp.Callable[..., tp.Any]:

        @functools.wraps(func)
        def wrapper_func(*args: tp.Any, **kwargs: tp.Any) -> tp.Any:
            __check_required_args_impl(required_args, kwargs)
            return func(*args, **kwargs)

        return wrapper_func

    return decorator_pp


def find_missing_revisions(
        data: tp.Generator[tp.Any, None, None], git_path: Path, cmap: CommitMap,
        should_insert_revision: tp.Callable[[tp.Any, tp.Any], tp.
                                            Tuple[bool, float]],
        to_commit_hash: tp.Callable[[tp.Any], str],
        are_neighbours: tp.Callable[[str, str], bool]) -> tp.Set[str]:
    """
    Calculate a set of revisions that could be missing because the changes
    between certain points are to steep.
    """
    new_revs: tp.Set[str] = set()

    _, last_row = next(data)
    for _, row in data:
        should_insert, gradient = should_insert_revision(last_row, row)
        if should_insert:
            lhs_cm = to_commit_hash(last_row)
            rhs_cm = to_commit_hash(row)

            if are_neighbours(lhs_cm, rhs_cm):
                print("Found steep gradient between neighbours " +
                      "{lhs_cm} - {rhs_cm}: {gradient}".format(
                          lhs_cm=lhs_cm,
                          rhs_cm=rhs_cm,
                          gradient=round(gradient, 5)))
                print("Investigate: git -C {git_path} diff {lhs} {rhs}".format(
                    git_path=git_path, lhs=lhs_cm, rhs=rhs_cm))
            else:
                print("Unusual gradient between " +
                      "{lhs_cm} - {rhs_cm}: {gradient}".format(
                          lhs_cm=lhs_cm,
                          rhs_cm=rhs_cm,
                          gradient=round(gradient, 5)))
                new_rev_id = round(
                    (cmap.short_time_id(lhs_cm) + cmap.short_time_id(rhs_cm)) /
                    2.0)
                new_rev = cmap.c_hash(new_rev_id)
                print(
                    "-> Adding {rev} as new revision to the sample set".format(
                        rev=new_rev))
                new_revs.add(new_rev)
        last_row = row
    return new_revs
