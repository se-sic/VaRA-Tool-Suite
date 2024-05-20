"""Project file for the feature performance case study collection."""
import typing as tp
from abc import abstractmethod

from benchbuild.command import SourceRoot, WorkloadSet
from benchbuild.source import Git
from benchbuild.utils.revision_ranges import RevisionRange

from varats.experiment.workload_util import (
    RSBinary,
    WorkloadCategory,
    ConfigParams,
)
from varats.paper.paper_config import (
    PaperConfigSpecificGit,
    project_filter_generator,
)
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_git_path,
)
from varats.project.sources import FeatureSource
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.projects.perf_tests.feature_perf_cs_collection_utils import (
    do_feature_perf_cs_collection_compile,
    do_feature_perf_cs_collection_recompile,
)
from varats.utils.git_util import RevisionBinaryMap, ShortCommitHash

if tp.TYPE_CHECKING:
    from benchbuild.project import Workloads, Sources


def _perf_inter_cs_source(project_name: str) -> "Sources":
    return [
        Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="PerformanceInteractionCaseStudy",
            refspec="origin/f-PerformanceInteractionDetection",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator(project_name)
        ),
        FeatureSource(),
    ]


def _perf_inter_cs_workload(project_name: str, binary_name: str) -> "Workloads":
    return {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot(project_name) / RSBinary(binary_name),
                ConfigParams(),
                label="default"
            )
        ]
    }


def _perf_inter_cs_binary(binary_name: str) -> RevisionBinaryMap:
    return RevisionBinaryMap(
        get_local_project_git_path(InterStructural.NAME)
    ).specify_binary(
        f"build/bin/{binary_name}",
        BinaryType.EXECUTABLE,
        only_valid_in=RevisionRange("03307d23ab", "HEAD")
    )


class PerformanceInteractionCaseStudy(VProject):
    """Base class for performance interaction case studies."""

    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    @staticmethod
    @abstractmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        ...

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        do_feature_perf_cs_collection_compile(self)

    def recompile(self) -> None:
        """Recompile the project."""
        do_feature_perf_cs_collection_recompile(self)


################################################################################
# Feature interaction pattern case studies
################################################################################


class InterStructural(PerformanceInteractionCaseStudy):
    """
    Feature interaction case study (Structural):

    Feature F1 interacts structurally with performance-relevant code, i.e., code
    from F1 is part of a performance-relevant code region.
    """
    NAME = "InterStructural"
    SOURCE = _perf_inter_cs_source(NAME)
    WORKLOADS = _perf_inter_cs_workload(NAME, "InteractionStructural")

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _perf_inter_cs_binary("InteractionStructural")[revision]


class InterDataFlow(PerformanceInteractionCaseStudy):
    """
    Feature interaction case study (Data Flow):

    Feature F1 interacts with performance-relevant code via data flow, i.e.,
    data flows from code from F1 to performance-relevant code.
    """
    NAME = "InterDataFlow"
    SOURCE = _perf_inter_cs_source(NAME)
    WORKLOADS = _perf_inter_cs_workload(NAME, "InteractionDataFlow")

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _perf_inter_cs_binary("InteractionDataFlow")[revision]


class InterImplicitFlow(PerformanceInteractionCaseStudy):
    """
    Feature interaction case study (Implicit Flow):

    Code from F1 influences program state such that it implicitly affects data
    that flows to performance-relevant code.
    """
    NAME = "InterImplicitFlow"
    SOURCE = _perf_inter_cs_source(NAME)
    WORKLOADS = _perf_inter_cs_workload(NAME, "InteractionImplicitFlow")

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _perf_inter_cs_binary("InteractionImplicitFlow")[revision]


################################################################################
# Interaction degree case studies
################################################################################

################################################################################
# Performance-relevant code case studies
################################################################################
