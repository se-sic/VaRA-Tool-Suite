"""Utility module for BenchBuild experiments."""

import os
import random
import resource
import traceback
import typing as tp
from abc import abstractmethod
from pathlib import Path

from benchbuild.experiment import Experiment
from benchbuild.project import Project
from benchbuild.utils.actions import Step, StepResult
from benchbuild.utils.cmd import prlimit
from plumbum.commands import ProcessExecutionError

from varats.data.report import BaseReport, FileStatusExtension
from varats.data.revisions import get_tagged_revisions
from varats.settings import vara_cfg, bb_cfg


class PEErrorHandler():
    """Error handler for process execution errors."""

    def __init__(
        self,
        result_folder: str,
        error_file_name: str,
        timeout_duration: tp.Optional[str] = None,
        delete_files: tp.Optional[tp.List[Path]] = None
    ):
        self.__result_folder = result_folder
        self.__error_file_name = error_file_name
        self.__timeout_duration = timeout_duration
        self.__delete_files = delete_files

    def __call__(self, ex: Exception, func: tp.Callable[..., tp.Any]) -> None:
        if self.__delete_files is not None:
            for delete_file in self.__delete_files:
                try:
                    delete_file.unlink()
                except FileNotFoundError:
                    pass

        error_file = Path(
            "{res_folder}/{res_file}".format(
                res_folder=self.__result_folder,
                res_file=self.__error_file_name
            )
        )
        if not os.path.exists(self.__result_folder):
            os.makedirs(self.__result_folder, exist_ok=True)
        with open(error_file, 'w') as outfile:
            if isinstance(ex, ProcessExecutionError):
                if ex.retcode == 124:
                    timeout_duration = str(self.__timeout_duration)
                    extra_error = f"""Command:
{str(func)}
Timeout after: {timeout_duration}

"""
                    outfile.write(extra_error)
                    outfile.flush()

            outfile.write("-----\nTraceback:\n")
            traceback.print_exc(file=outfile)

        raise ex


class FunctionPEErrorWrapper():
    """
    Wrap a function call with an exception handler.

    Args:
        func: function to be executed
        handler: function to handle exception
    """

    def __init__(
        self, func: tp.Callable[..., tp.Any], handler: PEErrorHandler
    ) -> None:
        self.__func = func
        self.__handler = handler

    def __call__(self, *args: tp.Any, **kwargs: tp.Any) -> tp.Any:
        try:
            return self.__func(*args, **kwargs)
        except Exception as ex:  # pylint: disable=broad-except
            self.__handler(ex, self.__func)


def exec_func_with_pe_error_handler(
    func: tp.Callable[..., tp.Any], handler: PEErrorHandler
) -> None:
    """
    Execute a function call with an exception handler.

    Args:
        func: function to be executed
        handler: function to handle exception
    """
    FunctionPEErrorWrapper(func, handler)()


def get_default_compile_error_wrapped(
    project: Project, report_type: tp.Type[BaseReport],
    result_folder_template: str
) -> FunctionPEErrorWrapper:
    """
    Setup the default project compile function with an error handler.

    Args:
        project: that will be compiled
        report_type: that should be generated
        result_folder_template: where the results will be placed

    Returns:
        project compilation function, wrapped with automatic error handling
    """
    result_dir = str(bb_cfg()["varats"]["outfile"])
    result_folder = result_folder_template.format(
        result_dir=result_dir, project_dir=str(project.name)
    )
    return FunctionPEErrorWrapper(
        project.compile,
        PEErrorHandler(
            result_folder,
            report_type.get_file_name(
                project_name=str(project.name),
                binary_name="all",
                project_version=str(project.version),
                project_uuid=str(project.run_uuid),
                extension_type=FileStatusExtension.CompileError,
                file_ext=".txt"
            )
        )
    )


def wrap_unlimit_stack_size(
    cmd: tp.Callable[..., tp.Any]
) -> tp.Callable[..., tp.Any]:
    """
    Wraps a command with prlimit to be executed with max stack size, i.e.,
    setting the soft limit to the hard limit.

    Args:
        cmd: command that should be executed with max stack size

    Returns: wrapped command
    """
    return prlimit["--stack=17179869184:", cmd]


class VersionExperiment(Experiment):  # type: ignore
    """Base class for experiments that want to analyze different project
    revisions."""

    @abstractmethod
    def actions_for_project(self, project: Project) -> tp.List[Step]:
        """Get the actions a project wants to run."""

    @staticmethod
    def _sample_num_versions(versions: tp.List[str]) -> tp.List[str]:
        if vara_cfg()["experiment"]["sample_limit"].value is None:
            return versions

        sample_size = int(vara_cfg()["experiment"]["sample_limit"])
        versions = [
            versions[i] for i in sorted(
                random.
                sample(range(len(versions)), min(sample_size, len(versions)))
            )
        ]
        return versions

    def sample(
        self,
        prj_cls: tp.Type[Project],
        versions: tp.Optional[tp.List[str]] = None
    ) -> tp.Generator[str, None, None]:
        """
        Adapt version sampling process if needed, otherwise fallback to default
        implementation.

        Args:
            prj_cls: project class
            versions: full list of versions to sample from

        Returns:
            generator that outputs a sequence of sampled versions
        """
        if versions is None:
            versions = []

        if bool(vara_cfg()["experiment"]["random_order"]):
            random.shuffle(versions)

        fs_blacklist = vara_cfg()["experiment"]["file_status_blacklist"].value
        fs_whitelist = vara_cfg()["experiment"]["file_status_whitelist"].value

        if fs_blacklist or fs_whitelist:
            fs_good = set(FileStatusExtension) if not fs_whitelist else set()

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
                    "Experiment sub class does not implement REPORT_TYPE."
                )

            for revision, file_status in get_tagged_revisions(
                prj_cls, getattr(self, 'REPORT_TYPE')
            ):
                if file_status not in fs_good and revision in versions:
                    versions.remove(revision)

            if not versions:
                print("Could not find any unprocessed versions.")
                return

            head, *tail = self._sample_num_versions(versions)
            yield head
            if bool(bb_cfg()["versions"]["full"]):
                for version in tail:
                    yield version
        else:
            versions = self._sample_num_versions(versions)

            for val in Experiment.sample(self, prj_cls, versions):
                yield val
