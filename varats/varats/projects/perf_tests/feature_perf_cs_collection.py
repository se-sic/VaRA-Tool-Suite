"""Project file for the feature performance case study collection."""
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.command import Command, SourceRoot, WorkloadSet
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
    get_local_project_git_path,
    verify_binaries,
)
from varats.project.sources import FeatureSource
from varats.project.varats_command import VCommand
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

    CONTAINER = get_base_image(ImageBase.DEBIAN_12)

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
            refspec="origin/HEAD",
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

    CONTAINER = get_base_image(ImageBase.DEBIAN_12)

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
            Command(
                SourceRoot("SynthSAFlowSensitivity") / RSBinary("FlowSense"),
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
            get_local_project_git_path(SynthSAFlowSensitivity.NAME)
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
            Command(
                SourceRoot("SynthSAContextSensitivity") /
                RSBinary("ContextSense"),
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
            get_local_project_git_path(SynthSAContextSensitivity.NAME)
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
            Command(
                SourceRoot("SynthSAWholeProgram") / RSBinary("WholeProgram"),
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
            get_local_project_git_path(SynthSAWholeProgram.NAME)
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
            Command(
                SourceRoot("SynthDADynamicDispatch") /
                RSBinary("DynamicDispatch"),
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
            get_local_project_git_path(SynthDADynamicDispatch.NAME)
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
            Command(
                SourceRoot("SynthDARecursion") / RSBinary("Recursion"),
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
            get_local_project_git_path(SynthDARecursion.NAME)
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
            Command(
                SourceRoot("SynthOVInsideLoop") / RSBinary("InsideLoop"),
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
            get_local_project_git_path(SynthOVInsideLoop.NAME)
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
            Command(
                SourceRoot("SynthFeatureInteraction") /
                RSBinary("FeatureInteraction"),
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
            get_local_project_git_path(SynthFeatureInteraction.NAME)
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
            Command(
                SourceRoot("SynthFeatureHigherOrderInteraction") /
                RSBinary("HigherOrderInteraction"),
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
            get_local_project_git_path(SynthFeatureHigherOrderInteraction.NAME)
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
        HTTPMultiple(
            local="geo-maps",
            remote={
                "1.0":
                    "https://github.com/simonepri/geo-maps/releases/"
                    "download/v0.6.0"
            },
            files=["countries-land-1km.geo.json", "countries-land-1m.geo.json"]
        )
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.SMALL): [
            VCommand(
                SourceRoot("SynthIPRuntime") / RSBinary("Runtime"),
                ConfigParams("-c"),
                "<",
                "geo-maps/countries-land-1km.geo.json",
                ">",
                "geo-maps/countries-land-1km.geo.json.compressed",
                label="countries-land-1km",
                creates=["geo-maps/countries-land-1km.geo.json.compressed"],
                requires_all_args={"-c"}
            )
        ],
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("SynthIPRuntime") / RSBinary("Runtime"),
                ConfigParams("-c"),
                "<",
                "geo-maps/countries-land-1m.geo.json",
                ">",
                "geo-maps/countries-land-1m.geo.json.compressed",
                label="countries-land-1m",
                creates=["geo-maps/countries-land-1m.geo.json.compressed"],
                requires_all_args={"-c"}
            )
        ],
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return RevisionBinaryMap(
            get_local_project_git_path(SynthIPRuntime.NAME)
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
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.SMALL): [
            VCommand(
                SourceRoot("SynthIPTemplate") / RSBinary("Template"),
                "<",
                "geo-maps/countries-land-1km.geo.json",
                ">",
                "geo-maps/countries-land-1km.geo.json.compressed",
                label="countries-land-1km",
                creates=["geo-maps/countries-land-1km.geo.json.compressed"],
                requires_all_patch={"Compress"}
            )
        ],
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("SynthIPTemplate") / RSBinary("Template"),
                "<",
                "geo-maps/countries-land-1m.geo.json",
                ">",
                "geo-maps/countries-land-1m.geo.json.compressed",
                label="countries-land-1m",
                creates=["geo-maps/countries-land-1m.geo.json.compressed"],
                requires_all_patch={"Compress"}
            )
        ],
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return RevisionBinaryMap(
            get_local_project_git_path(SynthIPTemplate.NAME)
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
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.SMALL): [
            VCommand(
                SourceRoot("SynthIPTemplate2") / RSBinary("Template2"),
                "<",
                "geo-maps/countries-land-1km.geo.json",
                ">",
                "geo-maps/countries-land-1km.geo.json.compressed",
                label="countries-land-1km",
                creates=["geo-maps/countries-land-1km.geo.json.compressed"],
                requires_all_patch={"Compress"}
            )
        ],
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("SynthIPTemplate2") / RSBinary("Template2"),
                "<",
                "geo-maps/countries-land-1m.geo.json",
                ">",
                "geo-maps/countries-land-1m.geo.json.compressed",
                label="countries-land-1m",
                creates=["geo-maps/countries-land-1m.geo.json.compressed"],
                requires_all_patch={"Compress"}
            )
        ],
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return RevisionBinaryMap(
            get_local_project_git_path(SynthIPTemplate2.NAME)
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
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.SMALL): [
            VCommand(
                SourceRoot("SynthIPCombined") / RSBinary("Combined"),
                ConfigParams("-c"),
                "<",
                "geo-maps/countries-land-1km.geo.json",
                ">",
                "geo-maps/countries-land-1km.geo.json.compressed",
                label="countries-land-1km",
                creates=["geo-maps/countries-land-1km.geo.json.compressed"],
                requires_all_args={"-c"}
            )
        ],
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("SynthIPCombined") / RSBinary("Combined"),
                ConfigParams("-c"),
                "<",
                "geo-maps/countries-land-1m.geo.json",
                ">",
                "geo-maps/countries-land-1m.geo.json.compressed",
                label="countries-land-1m",
                creates=["geo-maps/countries-land-1m.geo.json.compressed"],
                requires_all_args={"-c"}
            )
        ],
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return RevisionBinaryMap(
            get_local_project_git_path(SynthIPCombined.NAME)
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
