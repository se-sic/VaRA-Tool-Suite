"""Project file for the feature performance case study collection."""
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.command import Command, SourceRoot, WorkloadSet
from benchbuild.project import Workloads, Sources
from benchbuild.source import HTTPMultiple
from benchbuild.utils.cmd import make, cmake, mkdir
from benchbuild.utils.revision_ranges import RevisionRange
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.experiment.workload_util import (
    RSBinary,
    WorkloadCategory,
    ConfigParams,
)
from varats.paper.paper_config import project_filter_generator
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_repo,
    verify_binaries,
    RevisionBinaryMap,
)
from varats.project.sources import FeatureSource
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.utils.git_commands import init_all_submodules, update_all_submodules
from varats.utils.git_util import ShortCommitHash, RepositoryHandle
from varats.utils.settings import bb_cfg


def _do_feature_perf_cs_collection_compile(
    project: VProject, cmake_flag: str
) -> None:
    """Common compile function for FeaturePerfCSCollection projects."""
    feature_perf_repo = RepositoryHandle(Path(project.source_of_primary))

    cc_compiler = bb.compiler.cc(project)
    cxx_compiler = bb.compiler.cxx(project)

    mkdir("-p", feature_perf_repo.worktree_path / "build")

    init_all_submodules(feature_perf_repo)
    update_all_submodules(feature_perf_repo)

    with local.cwd(feature_perf_repo.worktree_path / "build"):
        with local.env(CC=str(cc_compiler), CXX=str(cxx_compiler)):
            bb.watch(cmake)("..", "-G", "Unix Makefiles", f"-D{cmake_flag}=ON")

        bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    with local.cwd(feature_perf_repo.worktree_path):
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

    CONTAINER = get_base_image(ImageBase.DEBIAN_12)

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_repo(FeaturePerfCSCollection.NAME)
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


class SynthSAFlowSensitivity(VProject):
    """Synthetic case-study project for testing flow sensitivity."""

    NAME = 'SynthSAFlowSensitivity'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="SynthSAFlowSensitivity",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("SynthSAFlowSensitivity")
        ),
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("SynthSAFlowSensitivity") / RSBinary("FlowSense"),
                ConfigParams(),
                label="FlowSense-no-input"
            )
        ]
    }

    CONTAINER = get_base_image(ImageBase.DEBIAN_12)

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_repo(SynthSAFlowSensitivity.NAME)
        )

        binary_map.specify_binary(
            "build/bin/FlowSense",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("0a9216d769", "master")
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
            refspec="origin/HEAD",
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
            VCommand(
                SourceRoot("SynthSAContextSensitivity") /
                RSBinary("ContextSense"),
                ConfigParams(),
                label="ContextSense-no-input"
            )
        ]
    }

    CONTAINER = get_base_image(ImageBase.DEBIAN_12)

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_repo(SynthSAContextSensitivity.NAME)
        )

        binary_map.specify_binary(
            "build/bin/ContextSense",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("0a9216d769", "master")
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
            refspec="origin/master",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("SynthSAWholeProgram")
        ),
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("SynthSAWholeProgram") / RSBinary("WholeProgram"),
                ConfigParams(),
                label="WholeProgram-no-input"
            )
        ]
    }

    CONTAINER = get_base_image(ImageBase.DEBIAN_12)

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_repo(SynthSAWholeProgram.NAME)
        )

        binary_map.specify_binary(
            "build/bin/WholeProgram",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("0a9216d769", "master")
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


class SynthDADynamicDispatch(VProject):
    """Synthetic case-study project for testing detection of virtual
    inheritance."""

    NAME = 'SynthDADynamicDispatch'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="SynthDADynamicDispatch",
            refspec="origin/master",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("SynthDADynamicDispatch")
        ),
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("SynthDADynamicDispatch") /
                RSBinary("DynamicDispatch"),
                ConfigParams(),
                label="DynamicDispatch-no-input"
            )
        ]
    }

    CONTAINER = get_base_image(ImageBase.DEBIAN_12)

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_repo(SynthDADynamicDispatch.NAME)
        )

        binary_map.specify_binary(
            "build/bin/DynamicDispatch",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("96848fadf1", "master")
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        _do_feature_perf_cs_collection_compile(
            self, "FPCSC_ENABLE_PROJECT_SYNTHDADYNAMICDISPATCH"
        )

    def recompile(self) -> None:
        """Recompile the project."""
        _do_feature_perf_cs_collection_recompile(self)


class SynthDARecursion(VProject):
    """Synthetic case-study project for testing detection of recursion."""

    NAME = 'SynthDARecursion'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="SynthDARecursion",
            refspec="origin/master",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("SynthDARecursion")
        ),
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("SynthDARecursion") / RSBinary("Recursion"),
                ConfigParams(),
                label="Recursion-no-input"
            )
        ]
    }

    CONTAINER = get_base_image(ImageBase.DEBIAN_12)

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_repo(SynthDARecursion.NAME)
        )

        binary_map.specify_binary(
            "build/bin/Recursion",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("96848fadf1", "master")
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        _do_feature_perf_cs_collection_compile(
            self, "FPCSC_ENABLE_PROJECT_SYNTHDARECURSION"
        )

    def recompile(self) -> None:
        """Recompile the project."""
        _do_feature_perf_cs_collection_recompile(self)


class SynthOVInsideLoop(VProject):
    """Synthetic case-study project for testing detection of hot loop codes."""

    NAME = 'SynthOVInsideLoop'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="SynthOVInsideLoop",
            refspec="origin/master",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("SynthOVInsideLoop")
        ),
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("SynthOVInsideLoop") / RSBinary("InsideLoop"),
                ConfigParams(),
                label="InsideLoop-no-input"
            )
        ]
    }

    CONTAINER = get_base_image(ImageBase.DEBIAN_12)

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_repo(SynthOVInsideLoop.NAME)
        )

        binary_map.specify_binary(
            "build/bin/InsideLoop",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("96848fadf1", "master")
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        _do_feature_perf_cs_collection_compile(
            self, "FPCSC_ENABLE_PROJECT_SYNTHOVINSIDELOOP"
        )

    def recompile(self) -> None:
        """Recompile the project."""
        _do_feature_perf_cs_collection_recompile(self)


class SynthFeatureInteraction(VProject):
    """Synthetic case-study project for testing detection of feature
    interactions."""

    NAME = 'SynthFeatureInteraction'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="SynthFeatureInteraction",
            refspec="origin/master",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("SynthFeatureInteraction")
        ),
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("SynthFeatureInteraction") /
                RSBinary("FeatureInteraction"),
                ConfigParams(),
                label="FeatureInteraction-no-input"
            )
        ]
    }

    CONTAINER = get_base_image(ImageBase.DEBIAN_12)

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_repo(SynthFeatureInteraction.NAME)
        )

        binary_map.specify_binary(
            "build/bin/FeatureInteraction",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("96848fadf1", "master")
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        _do_feature_perf_cs_collection_compile(
            self, "FPCSC_ENABLE_PROJECT_SYNTHFEATUREINTERACTION"
        )

    def recompile(self) -> None:
        """Recompile the project."""
        _do_feature_perf_cs_collection_recompile(self)


class SynthFeatureHigherOrderInteraction(VProject):
    """Synthetic case-study project for testing detection of higher-order
    feature interactions."""

    NAME = 'SynthFeatureHigherOrderInteraction'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="SynthFeatureHigherOrderInteraction",
            refspec="origin/master",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator(
                "SynthFeatureHigherOrderInteraction"
            )
        ),
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("SynthFeatureHigherOrderInteraction") /
                RSBinary("HigherOrderInteraction"),
                ConfigParams(),
                label="HigherOrderInteraction-no-input"
            )
        ]
    }

    CONTAINER = get_base_image(ImageBase.DEBIAN_12)

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_repo(SynthFeatureHigherOrderInteraction.NAME)
        )

        binary_map.specify_binary(
            "build/bin/HigherOrderInteraction",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("daf81de073", "master")
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        _do_feature_perf_cs_collection_compile(
            self, "FPCSC_ENABLE_PROJECT_SYNTHFEATUREHIGHERORDERINTERACTION"
        )

    def recompile(self) -> None:
        """Recompile the project."""
        _do_feature_perf_cs_collection_recompile(self)


def get_ip_workloads(project_source_name: str, binary_name: str) -> Workloads:
    return {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot(project_source_name) / RSBinary(binary_name),
                ConfigParams("-c"),
                label="countries-land-10km",
                creates=[
                    SourceRoot("geo-maps") /
                    "countries-land-10km.geo.json.compressed"
                ],
                requires_all_args={"-c"},
                redirect_stdin=SourceRoot("geo-maps") /
                "countries-land-10km.geo.json",
                redirect_stdout=SourceRoot("geo-maps") /
                "countries-land-10km.geo.json.compressed"
            ),
            VCommand(
                SourceRoot(project_source_name) / RSBinary(binary_name),
                ConfigParams("-d"),
                label="countries-land-10km",
                creates=[
                    SourceRoot("geo-maps-compr") /
                    "countries-land-10km.geo.json"
                ],
                requires_all_args={"-d"},
                redirect_stdin=SourceRoot("geo-maps-compr") /
                "countries-land-10km.geo.json.compressed",
                redirect_stdout=SourceRoot("geo-maps-compr") /
                "countries-land-10km.geo.json"
            )
        ],
        WorkloadSet(WorkloadCategory.SMALL): [
            VCommand(
                SourceRoot(project_source_name) / RSBinary(binary_name),
                ConfigParams("-c"),
                label="countries-land-500m",
                creates=[
                    SourceRoot("geo-maps") /
                    "countries-land-500m.geo.json.compressed"
                ],
                requires_all_args={"-c"},
                redirect_stdin=SourceRoot("geo-maps") /
                "countries-land-500m.geo.json",
                redirect_stdout=SourceRoot("geo-maps") /
                "countries-land-500m.geo.json.compressed"
            ),
            VCommand(
                SourceRoot(project_source_name) / RSBinary(binary_name),
                ConfigParams("-d"),
                label="countries-land-500m",
                creates=[
                    SourceRoot("geo-maps-compr") /
                    "countries-land-500m.geo.json"
                ],
                requires_all_args={"-d"},
                redirect_stdin=SourceRoot("geo-maps-compr") /
                "countries-land-500m.geo.json.compressed",
                redirect_stdout=SourceRoot("geo-maps-compr") /
                "countries-land-500m.geo.json"
            )
        ],
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot(project_source_name) / RSBinary(binary_name),
                ConfigParams("-c"),
                label="countries-land-250m",
                creates=[
                    SourceRoot("geo-maps") /
                    "countries-land-250m.geo.json.compressed"
                ],
                requires_all_args={"-c"},
                redirect_stdin=SourceRoot("geo-maps") /
                "countries-land-250m.geo.json",
                redirect_stdout=SourceRoot("geo-maps") /
                "countries-land-250m.geo.json.compressed"
            ),
            VCommand(
                SourceRoot(project_source_name) / RSBinary(binary_name),
                ConfigParams("-d"),
                label="countries-land-250m",
                creates=[
                    SourceRoot("geo-maps-compr") /
                    "countries-land-250m.geo.json"
                ],
                requires_all_args={"-d"},
                redirect_stdin=SourceRoot("geo-maps-compr") /
                "countries-land-250m.geo.json.compressed",
                redirect_stdout=SourceRoot("geo-maps-compr") /
                "countries-land-250m.geo.json"
            )
        ],
        WorkloadSet(WorkloadCategory.LARGE): [
            VCommand(
                SourceRoot(project_source_name) / RSBinary(binary_name),
                ConfigParams("-c"),
                label="countries-land-1m",
                creates=[
                    SourceRoot("geo-maps") /
                    "countries-land-1m.geo.json.compressed"
                ],
                requires_all_args={"-c"},
                redirect_stdin=SourceRoot("geo-maps") /
                "countries-land-1m.geo.json",
                redirect_stdout=SourceRoot("geo-maps") /
                "countries-land-1m.geo.json.compressed"
            ),
            VCommand(
                SourceRoot(project_source_name) / RSBinary(binary_name),
                ConfigParams("-d"),
                label="countries-land-1m",
                creates=[
                    SourceRoot("geo-maps-compr") / "countries-land-1m.geo.json"
                ],
                requires_all_args={"-d"},
                redirect_stdin=SourceRoot("geo-maps-compr") /
                "countries-land-1m.geo.json.compressed",
                redirect_stdout=SourceRoot("geo-maps-compr") /
                "countries-land-1m.geo.json"
            )
        ],
    }


def get_ip_data_sources() -> tp.List[Sources]:
    # TODO: fix typing in benchbuild
    return [
        tp.cast(
            Sources,
            HTTPMultiple(
                local="geo-maps",
                remote={
                    "1.0":
                        "https://github.com/simonepri/geo-maps/releases/"
                        "download/v0.6.0"
                },
                files=[
                    "countries-land-10km.geo.json",
                    "countries-land-500m.geo.json",
                    "countries-land-250m.geo.json", "countries-land-1m.geo.json"
                ]
            )
        ),
        tp.cast(
            Sources,
            HTTPMultiple(
                local="geo-maps-compr",
                remote={
                    "1.0":
                        "https://github.com/se-sic/compression-data/raw/master/"
                        "example_comp/geo-maps/"
                },
                files=[
                    "countries-land-10km.geo.json.compressed",
                    "countries-land-1m.geo.json.compressed",
                    "countries-land-250m.geo.json.compressed",
                    "countries-land-500m.geo.json.compressed"
                ]
            )
        ),
    ]


class SynthIPRuntime(VProject):
    """Synthetic case-study project for testing flow sensitivity."""

    NAME = 'SynthIPRuntime'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="SynthIPRuntime",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("SynthIPRuntime")
        ),
        FeatureSource(),
        *get_ip_data_sources(),
    ]

    WORKLOADS = get_ip_workloads("SynthIPRuntime", "Runtime")

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return RevisionBinaryMap(
            get_local_project_repo(SynthIPRuntime.NAME)
        ).specify_binary(
            "build/bin/Runtime",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("4151c42ffe", "master")
        )[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        _do_feature_perf_cs_collection_compile(
            self, "FPCSC_ENABLE_PROJECT_SYNTHIPRUNTIME"
        )

    def recompile(self) -> None:
        """Recompile the project."""
        _do_feature_perf_cs_collection_recompile(self)


class SynthIPTemplate(VProject):
    """Synthetic case-study project for testing flow sensitivity."""

    NAME = 'SynthIPTemplate'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="SynthIPTemplate",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("SynthIPTemplate")
        ),
        FeatureSource(),
        *get_ip_data_sources(),
    ]

    WORKLOADS = get_ip_workloads("SynthIPTemplate", "Template")

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return RevisionBinaryMap(
            get_local_project_repo(SynthIPTemplate.NAME)
        ).specify_binary(
            "build/bin/Template",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("4151c42ffe", "master")
        )[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        _do_feature_perf_cs_collection_compile(
            self, "FPCSC_ENABLE_PROJECT_SYNTHIPTEMPLATE"
        )

    def recompile(self) -> None:
        """Recompile the project."""
        _do_feature_perf_cs_collection_recompile(self)


class SynthIPTemplate2(VProject):
    """Synthetic case-study project for testing flow sensitivity."""

    NAME = 'SynthIPTemplate2'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="SynthIPTemplate2",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("SynthIPTemplate2")
        ),
        FeatureSource(),
        *get_ip_data_sources(),
    ]

    WORKLOADS = get_ip_workloads("SynthIPTemplate2", "Template2")

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return RevisionBinaryMap(
            get_local_project_repo(SynthIPTemplate2.NAME)
        ).specify_binary(
            "build/bin/Template2",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("4151c42ffe", "master")
        )[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        _do_feature_perf_cs_collection_compile(
            self, "FPCSC_ENABLE_PROJECT_SYNTHIPTEMPLATE2"
        )

    def recompile(self) -> None:
        """Recompile the project."""
        _do_feature_perf_cs_collection_recompile(self)


class SynthIPCombined(VProject):
    """Synthetic case-study project for testing flow sensitivity."""

    NAME = 'SynthIPCombined'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="SynthIPCombined",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("SynthIPCombined")
        ),
        FeatureSource(),
        *get_ip_data_sources(),
    ]

    WORKLOADS = get_ip_workloads("SynthIPCombined", "Combined")

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return RevisionBinaryMap(
            get_local_project_repo(SynthIPCombined.NAME)
        ).specify_binary(
            "build/bin/Combined",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("4151c42ffe", "master")
        )[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        _do_feature_perf_cs_collection_compile(
            self, "FPCSC_ENABLE_PROJECT_SYNTHIPCOMBINED"
        )

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
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("SynthSAFieldSensitivity")
        ),
        FeatureSource(),
        *get_ip_data_sources(),
    ]

    WORKLOADS = get_ip_workloads("SynthSAFieldSensitivity", "FieldSense")

    CONTAINER = get_base_image(ImageBase.DEBIAN_12)

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_repo(SynthSAFieldSensitivity.NAME)
        )

        binary_map.specify_binary(
            "build/bin/FieldSense",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("0a9216d769", "master")
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


class SynthCTTraitBased(VProject):
    """Synthetic case-study project for testing flow sensitivity."""

    NAME = 'SynthCTTraitBased'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="SynthCTTraitBased",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("SynthCTTraitBased")
        ),
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("SynthCTTraitBased") / RSBinary("CTTraitBased"),
                label="CompileTime-TraitBased"
            )
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_repo(SynthCTTraitBased.NAME)
        )

        binary_map.specify_binary(
            "build/bin/CTTraitBased",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("6d50a6efd5", "master")
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        _do_feature_perf_cs_collection_compile(
            self, "FPCSC_ENABLE_PROJECT_SYNTHCTTRAITBASED"
        )

    def recompile(self) -> None:
        """Recompile the project."""
        _do_feature_perf_cs_collection_recompile(self)


class SynthCTPolicies(VProject):
    """Synthetic case-study project for compile time variability using
    policies."""

    NAME = 'SynthCTPolicies'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="SynthCTPolicies",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("SynthCTPolicies")
        ),
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("SynthCTPolicies") / RSBinary("CTPolicies"),
                label="CompileTime-Policies"
            )
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_repo(SynthCTPolicies.NAME)
        )

        binary_map.specify_binary(
            "build/bin/CTPolicies",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("6d50a6efd5", "master")
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        _do_feature_perf_cs_collection_compile(
            self, "FPCSC_ENABLE_PROJECT_SYNTHCTPOLICIES"
        )

    def recompile(self) -> None:
        """Recompile the project."""
        _do_feature_perf_cs_collection_recompile(self)


class SynthCTCRTP(VProject):
    """Synthetic case-study project for compile time variability using CRTP."""

    NAME = 'SynthCTCRTP'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local=NAME,
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator(NAME)
        ),
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot(NAME) / RSBinary("CTCRTP"), label="CompileTime-CRTP"
            )
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(SynthCTCRTP.NAME))

        binary_map.specify_binary(
            "build/bin/CTCRTP",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("6d50a6efd5", "master")
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        _do_feature_perf_cs_collection_compile(
            self, "FPCSC_ENABLE_PROJECT_SYNTHCTCRTP"
        )

    def recompile(self) -> None:
        """Recompile the project."""
        _do_feature_perf_cs_collection_recompile(self)


class SynthCTTemplateSpecialization(VProject):
    """Synthetic case-study project for compile time variability using template
    specialization."""

    NAME = 'SynthCTTemplateSpecialization'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local=NAME,
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator(NAME)
        ),
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot(NAME) / RSBinary("CTTemplateSpecialization"),
                label="CompileTime-Template-Specialization"
            )
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_repo(SynthCTTemplateSpecialization.NAME)
        )

        binary_map.specify_binary(
            "build/bin/CTTemplateSpecialization",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("6d50a6efd5", "master")
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        _do_feature_perf_cs_collection_compile(
            self, "FPCSC_ENABLE_PROJECT_SYNTHCTSPECIALIZATION"
        )

    def recompile(self) -> None:
        """Recompile the project."""
        _do_feature_perf_cs_collection_recompile(self)


class SynthFeatureLargeConfigSpace(VProject):
    """Synthetic case-study project for testing flow sensitivity."""

    NAME = 'SynthFeatureLargeConfigSpace'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="SynthFeatureLargeConfigSpace",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator(
                "SynthFeatureLargeConfigSpace"
            )
        ),
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("SynthFeatureLargeConfigSpace") /
                RSBinary("LargeConfigSpace"),
                ConfigParams(),
                label="RestrictedConfigSpace-no-input"
            )
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return RevisionBinaryMap(
            get_local_project_repo(SynthFeatureLargeConfigSpace.NAME)
        ).specify_binary(
            "build/bin/LargeConfigSpace",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("6863c78c24", "HEAD")
        )[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        _do_feature_perf_cs_collection_compile(
            self, "FPCSC_ENABLE_PROJECT_SYNTHFEATURELARGECONFIGSPACE"
        )

    def recompile(self) -> None:
        """Recompile the project."""
        _do_feature_perf_cs_collection_recompile(self)


class SynthFeatureRestrictedConfigSpace(VProject):
    """Synthetic case-study project for testing flow sensitivity."""

    NAME = 'SynthFeatureRestrictedConfigSpace'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="SynthFeatureRestrictedConfigSpace",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator(
                "SynthFeatureRestrictedConfigSpace"
            )
        ),
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("SynthFeatureRestrictedConfigSpace") /
                RSBinary("RestrictedConfigSpace"),
                ConfigParams(),
                label="RestrictedConfigSpace-no-input"
            )
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return RevisionBinaryMap(
            get_local_project_repo(SynthFeatureRestrictedConfigSpace.NAME)
        ).specify_binary(
            "build/bin/RestrictedConfigSpace",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("6863c78c24", "HEAD")
        )[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        _do_feature_perf_cs_collection_compile(
            self, "FPCSC_ENABLE_PROJECT_SYNTHFEATURERESTRICTEDCONFIGSPACE"
        )

    def recompile(self) -> None:
        """Recompile the project."""
        _do_feature_perf_cs_collection_recompile(self)
