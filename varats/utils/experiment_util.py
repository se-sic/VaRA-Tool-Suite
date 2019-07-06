"""
Utility module for BenchBuild experiments.
"""

import typing as tp
import random

from plumbum.commands import ProcessExecutionError

from benchbuild.experiment import Experiment
from benchbuild.project import Project
from benchbuild.settings import CFG

from varats.settings import CFG as V_CFG
from varats.data.revisions import get_proccessed_revisions

class FunctionPEErrorWrapper():
    """
    Wrap a function call with a ProcessExecutionError handler.

    Args:
        handler: function to handle ProcessExecutionError
    """

    def __init__(self, func: tp.Callable[..., tp.Any],
                 handler: tp.Callable[[ProcessExecutionError], None]) -> None:
        self.__func = func
        self.__handler = handler

    def __call__(self, *args: tp.Any, **kwargs: tp.Any) -> tp.Any:
        try:
            return self.__func(*args, **kwargs)
        except ProcessExecutionError as ex:
            self.__handler(ex)


def exec_func_with_pe_error_handler(
        func: tp.Callable[..., tp.Any],
        handler: tp.Callable[[ProcessExecutionError], None]) -> None:
    """
    Execute a function call with a ProcessExecutionError handler.

    Args:
        handler: function to handle ProcessExecutionError
    """
    FunctionPEErrorWrapper(func, handler)()


class VaRAVersionExperiment(Experiment):  # type: ignore
    @staticmethod
    def __sample_num_versions(versions: tp.List[str]) -> tp.List[str]:
        sample_size = int(V_CFG["experiment"]["sample_limit"])
        versions = [
            versions[i] for i in sorted(
                random.sample(
                    range(len(versions)), min(sample_size, len(versions))))
        ]
        return versions

    def sample(self, prj_cls: tp.Type[Project],
               versions: tp.List[str]) -> tp.Generator[str, None, None]:
        """
        Adapt version sampling process if needed, otherwise fallback to default
        implementation.
        """
        if bool(V_CFG["experiment"]["random_order"]):
            random.shuffle(versions)

        if bool(V_CFG["experiment"]["only_missing"]):
            if not hasattr(self, 'REPORT_TYPE'):
                raise TypeError("Sub class does not implement REPORT_TYPE.")
            versions = [
                vers for vers in versions
                if vers not in get_proccessed_revisions(
                    prj_cls.NAME, getattr(self, 'REPORT_TYPE'))
            ]
            if not versions:
                print("Could not find any unprocessed versions.")
                return

            if V_CFG["experiment"]["sample_limit"].value is not None:
                versions = self.__sample_num_versions(versions)

            head, *tail = versions
            yield head
            if bool(CFG["versions"]["full"]):
                for version in tail:
                    yield version
        else:
            if V_CFG["experiment"]["sample_limit"].value is not None:
                versions = self.__sample_num_versions(versions)

            for val in Experiment.sample(self, prj_cls, versions):
                yield val
