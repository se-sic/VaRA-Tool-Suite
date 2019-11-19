"""
Utility module for BenchBuild experiments.
"""

import os
import typing as tp
import random
import traceback
from pathlib import Path
from abc import abstractmethod

from plumbum.commands import ProcessExecutionError
from plumbum.commands.base import BoundCommand

from benchbuild.experiment import Experiment
from benchbuild.project import Project
from benchbuild.utils.actions import Step
from benchbuild.settings import CFG

from varats.data.revisions import get_tagged_revisions
from varats.data.report import FileStatusExtension, BaseReport
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


def exec_func_with_pe_error_handler(func: tp.Callable[..., tp.Any],
                                    handler: tp.Callable[[Exception], None]
                                   ) -> None:
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
                 timeout_duration: tp.Optional[str] = None,
                 delete_files: tp.Optional[tp.List[Path]] = None):
        self.__result_folder = result_folder
        self.__error_file_name = error_file_name
        self.__run_cmd = run_cmd
        self.__timeout_duration = timeout_duration
        self.__delete_files = delete_files

    def __call__(self, ex: Exception) -> None:
        if self.__delete_files is not None:
            for delete_file in self.__delete_files:
                try:
                    delete_file.unlink()
                except FileNotFoundError:
                    pass

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

            outfile.write("-----\nException:\n")
            outfile.write(str(ex) + "\n")
            outfile.write("-----\nTraceback:\n")
            traceback.print_exc(file=outfile)

        raise ex


def get_default_compile_error_wrapped(project: Project,
                                      report_type: tp.Type[BaseReport],
                                      result_folder_template: str
                                     ) -> FunctionPEErrorWrapper:
    """
    Setup the default project compile function with an error handler.
    """
    return FunctionPEErrorWrapper(
        project.compile,
        PEErrorHandler(
            result_folder_template.format(result_dir=str(
                CFG["vara"]["outfile"]),
                                          project_dir=str(project.name)),
            report_type.get_file_name(
                project_name=str(project.name),
                binary_name="all",
                project_version=str(project.version),
                project_uuid=str(project.run_uuid),
                extension_type=FileStatusExtension.CompileError,
                file_ext=".txt")))


class VersionExperiment(Experiment):  # type: ignore
    """
    Base class for experiments that want to analyze different project
    revisions.
    """

    @abstractmethod
    def actions_for_project(self, project: Project) -> tp.List[Step]:
        """Get the actions a project wants to run."""

    @staticmethod
    def _sample_num_versions(versions: tp.List[str]) -> tp.List[str]:
        if V_CFG["experiment"]["sample_limit"].value is None:
            return versions

        sample_size = int(V_CFG["experiment"]["sample_limit"])
        versions = [
            versions[i] for i in sorted(
                random.sample(range(len(versions)),
                              min(sample_size, len(versions))))
        ]
        return versions

    def sample(self,
               prj_cls: tp.Type[Project],
               versions: tp.Optional[tp.List[str]] = None
              ) -> tp.Generator[str, None, None]:
        """
        Adapt version sampling process if needed, otherwise fallback to default
        implementation.
        """
        if versions is None:
            versions = []

        if bool(V_CFG["experiment"]["random_order"]):
            random.shuffle(versions)

        fs_blacklist = V_CFG["experiment"]["file_status_blacklist"].value
        fs_whitelist = V_CFG["experiment"]["file_status_whitelist"].value

        if fs_blacklist or fs_whitelist:
            fs_good = {x for x in FileStatusExtension
                      } if not fs_whitelist else set()

            fs_good -= {
                FileStatusExtension.get_file_status_from_str(x)
                for x in fs_blacklist
            }
            fs_good |= {
                FileStatusExtension.get_file_status_from_str(x)
                for x in fs_whitelist
            }

            if not hasattr(self, 'REPORT_TYPE'):
                raise TypeError(
                    "Experiment sub class does not implement REPORT_TYPE.")

            for revision, file_status in get_tagged_revisions(
                    prj_cls.NAME, getattr(self, 'REPORT_TYPE')):
                if file_status not in fs_good and revision in versions:
                    versions.remove(revision)

            if not versions:
                print("Could not find any unprocessed versions.")
                return

            head, *tail = self._sample_num_versions(versions)
            yield head
            if bool(CFG["versions"]["full"]):
                for version in tail:
                    yield version
        else:
            versions = self._sample_num_versions(versions)

            for val in Experiment.sample(self, prj_cls, versions):
                yield val
