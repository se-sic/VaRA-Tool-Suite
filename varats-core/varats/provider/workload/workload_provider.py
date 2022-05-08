"""
Module for the :class:`WorkloadProvider`.

TODO Won't work on other computers since we are using hard-coded paths. Replace
this with proper implementation for workloads.
"""

import typing as tp

from benchbuild.project import Project

from varats.projects.c_projects.brotli import Brotli
from varats.projects.c_projects.bzip2 import Bzip2
from varats.projects.c_projects.gzip import Gzip
from varats.projects.c_projects.xz import Xz
from varats.projects.perf_tests.feature_perf_cs_collection import (
    FeaturePerfCSCollection,
)
from varats.provider.provider import Provider


class WorkloadProvider(Provider):
    """Provider for a list of arguments to execute binaries in a project
    with."""

    WORKLOADS = {
        f"{FeaturePerfCSCollection.NAME},SimpleSleepLoop": [
            "--iterations", "100000", "--sleepns", "50000"
        ],
        f"{FeaturePerfCSCollection.NAME},SimpleBusyLoop": [
            "--iterations", "100000", "--count_to", "100000"
        ],
        f"{Xz.NAME},xz": [
            "-k", "-f", "-9e", "--compress", "--threads=8", "--format=xz",
            "/home/jonask/Repos/WorkloadsForConfigurableSystems/compression/countries-land-1km.geo.json"
        ],
        f"{Brotli.NAME},brotli": [
            "-f", "-o", "/tmp/brotli_compression_test.br",
            "/home/jonask/Repos/WorkloadsForConfigurableSystems/compression/countries-land-1km.geo.json"
        ],
        f"{Bzip2.NAME},bzip2": [
            "--compress", "--best", "--verbose", "--keep", "--force",
            "/home/jonask/Repos/WorkloadsForConfigurableSystems/compression/countries-land-1m.geo.json"
        ],
        f"{Gzip.NAME},gzip": [
            "--force", "--keep", "--name", "--recursive", "--verbose", "--best",
            "/home/jonask/Repos/WorkloadsForConfigurableSystems/compression/countries-land-10km.geo.json"
        ],
    }

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

    def get_workload_for_binary(self, binary_name: str) -> tp.List[str]:
        """Get a list of arguments to execute the given binary with."""
        key = f"{self.project.NAME},{binary_name}"
        return self.WORKLOADS.get(key, None)
