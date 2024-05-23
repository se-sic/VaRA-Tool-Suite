"""Module for performance interaction reports."""
import logging
import typing as tp
from pathlib import Path

import yaml

from varats.base.version_header import VersionHeader
from varats.report.multi_patch_report import MultiPatchReport
from varats.report.report import BaseReport
from varats.utils.git_util import CommitRepoPair

LOG = logging.getLogger(__name__)


class PerfInteraction:

    def __init__(
        self, commit: CommitRepoPair, perf_region: str,
        involved_features: tp.List[str]
    ):
        self.__commit = commit
        self.__perf_region = perf_region
        self.__involved_features = involved_features

    @property
    def commit(self) -> CommitRepoPair:
        return self.__commit

    @property
    def performance_region(self) -> str:
        return self.__perf_region

    @property
    def involved_features(self) -> tp.List[str]:
        return self.__involved_features

    def __str__(self):
        return (
            f"{self.__commit} -> {self.__perf_region} "
            f"[{', '.join(self.__involved_features)}]"
        )


class PerformanceInteractionReport(
    BaseReport, shorthand="PIE", file_type="yaml"
):
    """Report with performance interactions."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.__perf_inters: tp.List[PerfInteraction] = []

        with open(path, 'r') as stream:
            documents = yaml.load_all(stream, Loader=yaml.CLoader)
            version_header = VersionHeader(next(documents))
            version_header.raise_if_not_type("PerfInterReport")
            version_header.raise_if_version_is_less_than(1)

            raw_report = next(documents)

            for raw_inter in raw_report['perf-inters']:
                self.__perf_inters.append(
                    PerfInteraction(
                        raw_inter['commit'],
                        raw_inter['perf'],
                        raw_inter['features'],
                    )
                )

    @property
    def performance_interactions(self) -> tp.Iterable[PerfInteraction]:
        """Get all performance interactions."""
        return self.__perf_inters

    def __str__(self) -> str:
        return "\n".join(map(str, self.__perf_inters))


class MPRPerformanceInteractionReport(
    MultiPatchReport[PerformanceInteractionReport],
    shorthand="MPRPIE",
    file_type=".zip"
):
    """Multi-patch wrapper report for performance interaction reports."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, PerformanceInteractionReport)
