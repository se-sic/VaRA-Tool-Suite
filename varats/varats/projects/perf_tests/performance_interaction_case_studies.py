"""Project file for the feature performance case study collection."""
import typing as tp

from benchbuild.command import SourceRoot, WorkloadSet
from benchbuild.utils.revision_ranges import RevisionRange

from varats.containers.containers import get_base_image, ImageBase
from varats.experiment.workload_util import (
    RSBinary,
    WorkloadCategory,
    ConfigParams,
)
from varats.paper.paper_config import PaperConfigSpecificGit
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
        PaperConfigSpecificGit(
            project_name,
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="PerformanceInteractionCaseStudies",
            refspec="origin/f-PerformanceInteractionDetection",
            limit=None,
            shallow=False
        ),
        FeatureSource(),
    ]


def _perf_inter_cs_workload(project_name: str, binary_name: str) -> "Workloads":
    return {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("PerformanceInteractionCaseStudies") /
                RSBinary(binary_name),
                ConfigParams(),
                label="default"
            )
        ]
    }


def _perf_inter_cs_binary(
    project_name: str, binary_name: str
) -> RevisionBinaryMap:
    return RevisionBinaryMap(
        get_local_project_git_path(project_name)
    ).specify_binary(
        f"build/bin/{binary_name}",
        BinaryType.EXECUTABLE,
        only_valid_in=RevisionRange("cf9a577906", "HEAD")
    )


################################################################################
# Feature interaction pattern case studies
################################################################################


class InterStructural(VProject):
    """
    Feature interaction case study (Structural):

    Feature F1 interacts structurally with performance-relevant code, i.e., code
    from F1 is part of a performance-relevant code region.
    """
    NAME = "InterStructural"
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = _perf_inter_cs_source(NAME)
    CONTAINER = get_base_image(ImageBase.DEBIAN_12)
    WORKLOADS = _perf_inter_cs_workload(NAME, "InterStructural")

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _perf_inter_cs_binary(InterStructural.NAME,
                                     "InterStructural")[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        do_feature_perf_cs_collection_compile(self)

    def recompile(self) -> None:
        """Recompile the project."""
        do_feature_perf_cs_collection_recompile(self)


class InterDataFlow(VProject):
    """
    Feature interaction case study (Data Flow):

    Feature F1 interacts with performance-relevant code via data flow, i.e.,
    data flows from code from F1 to performance-relevant code.
    """
    NAME = "InterDataFlow"
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = _perf_inter_cs_source(NAME)
    CONTAINER = get_base_image(ImageBase.DEBIAN_12)
    WORKLOADS = _perf_inter_cs_workload(NAME, "InterDataFlow")

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _perf_inter_cs_binary(InterDataFlow.NAME,
                                     "InterDataFlow")[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        do_feature_perf_cs_collection_compile(self)

    def recompile(self) -> None:
        """Recompile the project."""
        do_feature_perf_cs_collection_recompile(self)


class InterImplicitFlow(VProject):
    """
    Feature interaction case study (Implicit Flow):

    Code from F1 influences program state such that it implicitly affects data
    that flows to performance-relevant code.
    """
    NAME = "InterImplicitFlow"
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = _perf_inter_cs_source(NAME)
    CONTAINER = get_base_image(ImageBase.DEBIAN_12)
    WORKLOADS = _perf_inter_cs_workload(NAME, "InterImplicitFlow")

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _perf_inter_cs_binary(
            InterImplicitFlow.NAME, "InterImplicitFlow"
        )[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        do_feature_perf_cs_collection_compile(self)

    def recompile(self) -> None:
        """Recompile the project."""
        do_feature_perf_cs_collection_recompile(self)


################################################################################
# Interaction degree case studies
################################################################################


class DegreeLow(VProject):
    """
    Low interaction degree case study:

    Regression is triggered by a single feature.
    """
    NAME = "DegreeLow"
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = _perf_inter_cs_source(NAME)
    CONTAINER = get_base_image(ImageBase.DEBIAN_12)
    WORKLOADS = _perf_inter_cs_workload(NAME, "DegreeLow")

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _perf_inter_cs_binary(DegreeLow.NAME, "DegreeLow")[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        do_feature_perf_cs_collection_compile(self)

    def recompile(self) -> None:
        """Recompile the project."""
        do_feature_perf_cs_collection_recompile(self)


class DegreeHigh(VProject):
    """
    High interaction degree case study:

    Regression is triggered only if all 10 features are enabled.
    """
    NAME = "DegreeHigh"
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = _perf_inter_cs_source(NAME)
    CONTAINER = get_base_image(ImageBase.DEBIAN_12)
    WORKLOADS = _perf_inter_cs_workload(NAME, "DegreeHigh")

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _perf_inter_cs_binary(DegreeHigh.NAME, "DegreeHigh")[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        do_feature_perf_cs_collection_compile(self)

    def recompile(self) -> None:
        """Recompile the project."""
        do_feature_perf_cs_collection_recompile(self)


################################################################################
# Performance-relevant code case studies
################################################################################


class FunctionSingle(VProject):
    """
    Single hot function case study:

    Regression triggers if function1 is affected.
    """
    NAME = "FunctionSingle"
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = _perf_inter_cs_source(NAME)
    CONTAINER = get_base_image(ImageBase.DEBIAN_12)
    WORKLOADS = _perf_inter_cs_workload(NAME, "FunctionSingle")

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _perf_inter_cs_binary(FunctionSingle.NAME,
                                     "FunctionSingle")[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        do_feature_perf_cs_collection_compile(self)

    def recompile(self) -> None:
        """Recompile the project."""
        do_feature_perf_cs_collection_recompile(self)


class FunctionAccumulating(VProject):
    """
    Single hot function case study:

    Regression triggers if function1 is affected.
    """
    NAME = "FunctionAccumulating"
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = _perf_inter_cs_source(NAME)
    CONTAINER = get_base_image(ImageBase.DEBIAN_12)
    WORKLOADS = _perf_inter_cs_workload(NAME, "FunctionAccumulating")

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _perf_inter_cs_binary(
            FunctionAccumulating.NAME, "FunctionAccumulating"
        )[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        do_feature_perf_cs_collection_compile(self)

    def recompile(self) -> None:
        """Recompile the project."""
        do_feature_perf_cs_collection_recompile(self)


class FunctionMultiple(VProject):
    """
    Single hot function case study:

    Regression triggers if function1 is affected.
    """
    NAME = "FunctionMultiple"
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = _perf_inter_cs_source(NAME)
    CONTAINER = get_base_image(ImageBase.DEBIAN_12)
    WORKLOADS = _perf_inter_cs_workload(NAME, "FunctionMultiple")

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _perf_inter_cs_binary(FunctionMultiple.NAME,
                                     "FunctionMultiple")[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        do_feature_perf_cs_collection_compile(self)

    def recompile(self) -> None:
        """Recompile the project."""
        do_feature_perf_cs_collection_recompile(self)
