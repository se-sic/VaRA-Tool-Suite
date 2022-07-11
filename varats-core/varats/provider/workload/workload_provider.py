"""
Module for the :class:`WorkloadProvider`.

TODO (se-sic/VaRA#841): replace with bb workloads if possible
"""

import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.project import Project
from benchbuild.source.base import target_prefix

from varats.projects.c_projects.brotli import Brotli
from varats.projects.c_projects.bzip2 import Bzip2
from varats.projects.c_projects.gzip import Gzip
from varats.projects.c_projects.xz import Xz
from varats.projects.perf_tests.feature_perf_cs_collection import (
    FeaturePerfCSCollection,
)
from varats.provider.provider import Provider
from varats.utils.settings import vara_cfg


class WorkloadProvider(Provider):
    """Provider for a list of arguments to execute binaries in a project
    with."""

    def __init__(self, project: tp.Type[Project]) -> None:
        super().__init__(project)

        workloads_source = bb.source.Git(
            remote=(
                "https://gitlab.cs.uni-saarland.de/s8jskauf/"
                "WorkloadsForConfigurableSystems.git"
            ),
            local="WorkloadsForConfigurableSystems",
            refspec="origin/HEAD",
            limit=1,
        )
        workloads_source.fetch()
        self._workloads_base_dir = Path(
            Path(target_prefix()) / workloads_source.local
        )

        self._workloads = {
            f"{FeaturePerfCSCollection.NAME},SimpleSleepLoop": [
                "--iterations", 3 * 10**3, "--sleepms", 10
            ],
            f"{FeaturePerfCSCollection.NAME},SimpleBusyLoop": [
                "--iterations", 3 * 10**5, "--count_to", 10**5
            ],
            f"{Xz.NAME},xz": [
                "-k", "-f", "-9e", "--compress", "--threads=0", "--format=xz",
                "-vv",
                str(
                    self._workloads_base_dir /
                    "compression/countries-land-250m.geo.json"
                )
            ],
            f"{Brotli.NAME},brotli": [
                "-f", "-o", "/tmp/brotli_compression_test.br",
                str(
                    self._workloads_base_dir /
                    "compression/countries-land-1km.geo.json"
                )
            ],
            f"{Bzip2.NAME},bzip2": [
                "--compress", "--best", "--verbose", "--verbose", "--keep",
                "--force",
                str(
                    self._workloads_base_dir /
                    "compression/countries-land-1m.geo.json"
                ),
                str(
                    self._workloads_base_dir /
                    "compression/countries-land-10m.geo.json"
                ),
                str(
                    self._workloads_base_dir /
                    "compression/countries-land-100m.geo.json"
                )
            ],
            f"{Gzip.NAME},gzip": [
                "--force", "--keep", "--name", "--recursive", "--verbose",
                "--best",
                str(
                    self._workloads_base_dir /
                    "compression/countries-land-500m.geo.json"
                )
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

    def get_workload_for_binary(self,
                                binary_name: str) -> tp.Optional[tp.List[str]]:
        """Get a list of arguments to execute the given binary with."""
        key = f"{self.project.NAME},{binary_name}"
        return self._workloads.get(key, None)
