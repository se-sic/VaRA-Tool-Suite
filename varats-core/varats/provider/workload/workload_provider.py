"""Module for the :class:`WorkloadProvider`."""
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.project import Project
from benchbuild.source.base import target_prefix

from varats.provider.provider import Provider
from varats.project.project_util import ProjectBinaryWrapper


class WorkloadNotFound(FileNotFoundError):
    """Exception raised when the specified workload could not be found."""

    def __init__(self, project: Project, binary: ProjectBinaryWrapper) -> None:
        err_msg = f"Could not find workload for project {project.name} and binary {binary.name}"

        super().__init__(err_msg)


class WorkloadProvider(Provider):
    """Provider for accessing project related workloads."""

    @classmethod
    def create_provider_for_project(
        cls, project: tp.Type[Project]
    ) -> tp.Optional['WorkloadProvider']:
        """
        Creates a provider instance for the given project if possible.

        Returns:
            a provider instance for the given project if possible,
            otherwise, ``None``
        """
        return WorkloadProvider(project)

    @classmethod
    def create_default_provider(
        cls, project: tp.Type[Project]
    ) -> 'WorkloadProvider':
        """
        Creates a default provider instance that can be used with any project.

        Returns:
            a default provider instance
        """
        raise AssertionError(
            "All usages should be covered by the project specific provider."
        )

    WORKLOADS = {
        "SimpleSleepLoop": ["--iterations", "1000", "--sleepms", "5"],
        "SimpleBusyLoop": ["--iterations", "1000", "--count_to", "10000"],
        "xz": ["-k", "-f", "-7e", "--compress", "--threads=8", "--format=xz",
               "/home/jonask/Repos/WorkloadsForConfigurableSystems/xz/countries-land-1km.geo.json"],
        "brotli": ["-f", "-k", "-o", "/tmp/brotli_compression_test.br", "--best", "/home/jonask/Repos/WorkloadsForConfigurableSystems/brotli/countries-land-1km.geo.json"]
    }

    @classmethod
    def get_workload_parameters(
        self,
        binary: ProjectBinaryWrapper
    ) -> tp.Optional[list[str]]:
        """
        Get the runtime parameters for a specific binary of the project.
        In case that no workload exists, `None` is returned.

        Returns: a list of parameters to run the binary with
        """

        return WorkloadProvider.WORKLOADS.get(binary.name, None)

    # @staticmethod
    # def _get_workload_repository_path() -> Path:
    #     fm_source = bb.source.Git(
    #         remote="https://github.com/Kaufi-Jonas/ConfigurableSystems.git",
    #         local="ConfigurableSystems",
    #         refspec="origin/HEAD",
    #         limit=1,
    #     )
    #     fm_source.fetch()

    #     return Path(Path(target_prefix()) / fm_source.local)
