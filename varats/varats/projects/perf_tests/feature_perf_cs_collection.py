"""Project file for the feature performance case study collection."""
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.command import Command, SourceRoot, WorkloadSet
from benchbuild.utils.cmd import make, cmake, mkdir
from benchbuild.utils.revision_ranges import RevisionRange
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.experiment.workload_util import RSBinary, WorkloadCategory
from varats.paper.paper_config import project_filter_generator
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_git_path,
    verify_binaries,
)
from varats.project.sources import FeatureSource
from varats.project.varats_project import VProject
from varats.utils.git_commands import init_all_submodules, update_all_submodules
from varats.utils.git_util import RevisionBinaryMap, ShortCommitHash
from varats.utils.settings import bb_cfg


def _do_feature_perf_cs_collection_compile(
    project: VProject, cmake_flag: str
) -> None:
    """Common compile function for FeaturePerfCSCollection projects."""
    feature_perf_source = local.path(project.source_of(project.primary_source))

    cc_compiler = bb.compiler.cc(project)
    cxx_compiler = bb.compiler.cxx(project)

    mkdir("-p", feature_perf_source / "build")

    init_all_submodules(Path(feature_perf_source))
    update_all_submodules(Path(feature_perf_source))

    with local.cwd(feature_perf_source / "build"):
        with local.env(CC=str(cc_compiler), CXX=str(cxx_compiler)):
            bb.watch(cmake)("..", "-G", "Unix Makefiles", f"-D{cmake_flag}=ON")

        bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    with local.cwd(feature_perf_source):
        verify_binaries(project)


def _do_feature_perf_cs_collection_recompile(project: VProject) -> None:
    feature_perf_source = local.path(project.source_of(project.primary_source))

    with local.cwd(feature_perf_source / "build"):
        bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))


class FeaturePerfCSCollection(VProject):
    """Test project for feature performance case studies."""

    NAME = 'FeaturePerfCSCollection'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="FeaturePerfCSCollection",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("FeaturePerfCSCollection")
        ),
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            Command(
                SourceRoot("FeaturePerfCSCollection") /
                RSBinary("SingleLocalSimple"),
                label="SLS-no-input"
            ),
            Command(
                SourceRoot("FeaturePerfCSCollection") /
                RSBinary("MultiSharedMultipleRegions"),
                label="MSMR-no-input"
            ),
            Command(
                SourceRoot("FeaturePerfCSCollection") /
                RSBinary("SimpleFeatureInteraction"),
                "--enc",
                "--compress",
                label="SFI-enc-compress"
            )
        ],
        WorkloadSet(WorkloadCategory.MEDIUM): [
            Command(
                SourceRoot("FeaturePerfCSCollection") /
                RSBinary("SimpleBusyLoop"),
                "--iterations",
                str(10**7),
                "--count_to",
                str(5 * 10**3),
                label="SBL-iterations-10M-count-to-5K"
            )
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(FeaturePerfCSCollection.NAME)
        )

        binary_map.specify_binary(
            "build/bin/SingleLocalSimple", BinaryType.EXECUTABLE
        )
        binary_map.specify_binary(
            "build/bin/SingleLocalMultipleRegions",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("162db88346", "master")
        )
        binary_map.specify_binary(
            "build/bin/SimpleBusyLoop",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange(
                "c77bca4c6888970fb721069c82455137943ccf49", "master"
            )
        )
        binary_map.specify_binary(
            "build/bin/SimpleFeatureInteraction",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange(
                "c051e44a973ee31b3baa571407694467a513ba68", "master"
            )
        )
        binary_map.specify_binary(
            "build/bin/MultiSharedMultipleRegions",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange(
                "c051e44a973ee31b3baa571407694467a513ba68", "master"
            )
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        _do_feature_perf_cs_collection_compile(self, "FPCSC_ENABLE_SRC")

    def recompile(self) -> None:
        """Recompile the project."""
        _do_feature_perf_cs_collection_recompile(self)


class SynthSAFieldSensitivity(VProject):
    """Synthetic case-study project for testing field sensitivity."""

    NAME = 'SynthSAFieldSensitivity'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="SynthSAFieldSensitivity",
            refspec="origin/f-StaticAnalysisMotivatedSynthBenchmarksImpl",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("SynthSAFieldSensitivity")
        ),
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            Command(
                SourceRoot("SynthSAFieldSensitivity") / RSBinary("FieldSense"),
                label="FieldSense-no-input"
            )
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(SynthSAFieldSensitivity.NAME)
        )

        binary_map.specify_binary(
            "build/bin/FieldSense",
            BinaryType.EXECUTABLE,
            # TODO: fix with commit after merge
            # only_valid_in=RevisionRange("162db88346", "master")
            only_valid_in=RevisionRange(
                "162db88346", "f-StaticAnalysisMotivatedSynthBenchmarksImpl"
            )
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        _do_feature_perf_cs_collection_compile(
            self, "FPCSC_ENABLE_PROJECT_SYNTHSAFIELDSENSITIVITY"
        )

    def recompile(self) -> None:
        """Recompile the project."""
        _do_feature_perf_cs_collection_recompile(self)


class SynthSAFlowSensitivity(VProject):
    """Synthetic case-study project for testing flow sensitivity."""

    NAME = 'SynthSAFlowSensitivity'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="SynthSAFlowSensitivity",
            refspec="origin/f-StaticAnalysisMotivatedSynthBenchmarksImpl",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("SynthSAFlowSensitivity")
        ),
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            Command(
                SourceRoot("SynthSAFlowSensitivity") / RSBinary("FlowSense"),
                label="FlowSense-no-input"
            )
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(SynthSAFlowSensitivity.NAME)
        )

        binary_map.specify_binary(
            "build/bin/FlowSense",
            BinaryType.EXECUTABLE,
            # TODO: fix with commit after merge
            # only_valid_in=RevisionRange("162db88346", "master")
            only_valid_in=RevisionRange(
                "162db88346", "f-StaticAnalysisMotivatedSynthBenchmarksImpl"
            )
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        _do_feature_perf_cs_collection_compile(
            self, "FPCSC_ENABLE_PROJECT_SYNTHSAFLOWSENSITIVITY"
        )

    def recompile(self) -> None:
        """Recompile the project."""
        _do_feature_perf_cs_collection_recompile(self)


class SynthSAContextSensitivity(VProject):
    """Synthetic case-study project for testing flow sensitivity."""

    NAME = 'SynthSAContextSensitivity'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="SynthSAContextSensitivity",
            refspec="origin/f-StaticAnalysisMotivatedSynthBenchmarksImpl",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator(
                "SynthSAContextSensitivity"
            )
        ),
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            Command(
                SourceRoot("SynthSAContextSensitivity") /
                RSBinary("ContextSense"),
                label="ContextSense-no-input"
            )
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(SynthSAContextSensitivity.NAME)
        )

        binary_map.specify_binary(
            "build/bin/ContextSense",
            BinaryType.EXECUTABLE,
            # TODO: fix with commit after merge
            # only_valid_in=RevisionRange("162db88346", "master")
            only_valid_in=RevisionRange(
                "162db88346", "f-StaticAnalysisMotivatedSynthBenchmarksImpl"
            )
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        _do_feature_perf_cs_collection_compile(
            self, "FPCSC_ENABLE_PROJECT_SYNTHSACONTEXTSENSITIVITY"
        )

    def recompile(self) -> None:
        """Recompile the project."""
        _do_feature_perf_cs_collection_recompile(self)


class SynthSAWholeProgram(VProject):
    """Synthetic case-study project for testing flow sensitivity."""

    NAME = 'SynthSAWholeProgram'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="SynthSAWholeProgram",
            refspec="origin/f-StaticAnalysisMotivatedSynthBenchmarksImpl",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("SynthSAWholeProgram")
        ),
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            Command(
                SourceRoot("SynthSAWholeProgram") / RSBinary("WholeProgram"),
                label="WholeProgram-no-input"
            )
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(SynthSAWholeProgram.NAME)
        )

        binary_map.specify_binary(
            "build/bin/WholeProgram",
            BinaryType.EXECUTABLE,
            # TODO: fix with commit after merge
            # only_valid_in=RevisionRange("162db88346", "master")
            only_valid_in=RevisionRange(
                "162db88346", "f-StaticAnalysisMotivatedSynthBenchmarksImpl"
            )
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        _do_feature_perf_cs_collection_compile(
            self, "FPCSC_ENABLE_PROJECT_SYNTHSAWHOLEPROGRAM"
        )

    def recompile(self) -> None:
        """Recompile the project."""
        _do_feature_perf_cs_collection_recompile(self)
