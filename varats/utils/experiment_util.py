"""
Utility module for BenchBuild experiments.
"""

import os
import typing as tp
import random
from pathlib import Path

from plumbum.commands import ProcessExecutionError
from plumbum.commands.base import BoundCommand

from benchbuild.experiment import Experiment
from benchbuild.project import Project
from benchbuild.settings import CFG

from varats.data.revisions import get_processed_revisions
from varats.settings import CFG as V_CFG


class FunctionPEErrorWrapper():
    """
    Wrap a function call with an exception handler.

    Args:
        handler: function to handle exception
    """

    def __init__(self, func: tp.Callable[..., tp.Any],
                 handler: tp.Callable[[Exception], None]) -> None:
        self.__func = func
        self.__handler = handler

    def __call__(self, *args: tp.Any, **kwargs: tp.Any) -> tp.Any:
        try:
            return self.__func(*args, **kwargs)
        except Exception as ex:
            self.__handler(ex)


def exec_func_with_pe_error_handler(
        func: tp.Callable[..., tp.Any],
        handler: tp.Callable[[Exception], None]) -> None:
    """
    Execute a function call with an exception handler.

    Args:
        handler: function to handle exception
    """
    FunctionPEErrorWrapper(func, handler)()


class PEErrorHandler():
    """
    Error handler for process execution errors
    """

    def __init__(self,
                 result_folder: str,
                 error_file_name: str,
                 run_cmd: tp.Optional[BoundCommand] = None,
                 timeout_duration: tp.Optional[str] = None):
        self.__result_folder = result_folder
        self.__error_file_name = error_file_name
        self.__run_cmd = run_cmd
        self.__timeout_duration = timeout_duration

    def __call__(self, ex: Exception) -> None:
        error_file = Path("{res_folder}/{res_file}".format(
            res_folder=self.__result_folder, res_file=self.__error_file_name))
        if not os.path.exists(self.__result_folder):
            os.makedirs(self.__result_folder, exist_ok=True)
        with open(error_file, 'w') as outfile:
            if isinstance(ex, ProcessExecutionError):
                if ex.retcode == 124:
                    extra_error = """Command:
{cmd}
Timeout after: {timeout_duration}

""".format(cmd=str(self.__run_cmd),
                    timeout_duration=str(self.__timeout_duration))
                    outfile.write(extra_error)
                    outfile.flush()

            outfile.write("Exception:\n")
            outfile.write(str(ex))

        raise ex


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
                if vers not in get_processed_revisions(
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
