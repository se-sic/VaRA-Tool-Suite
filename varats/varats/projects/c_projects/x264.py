"""Project file for x264."""

import typing
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.command import SourceRoot, WorkloadSet
from benchbuild.source import HTTP
from benchbuild.utils.cmd import make
from benchbuild.utils.revision_ranges import GoodBadSubgraph, block_revisions
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import ImageBase, get_base_image
from varats.experiment.workload_util import (
    ConfigParams,
    RSBinary,
    WorkloadCategory,
)
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.patch_variation_source import PatchVariationSource
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    BinaryType,
    ProjectBinaryWrapper,
    RevisionBinaryMap,
    get_local_project_repo,
    verify_binaries,
)
from varats.project.sources import FeatureSource
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, get_all_revisions_between
from varats.utils.settings import bb_cfg
from varats.utils.testsuite_utils import TestResult


class X264(VProject):
    """Video encoder x264 (fetched by Git)"""

    NAME = 'x264'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.CODEC

    SOURCE: typing.ClassVar = [
        block_revisions(
            [
                GoodBadSubgraph(
                    ["5dc0aae2f900064d1f58579929a2285ab289a436"],
                    ["6490f4398d9e28e65d7517849e729e14eede8c5b"],
                    "Does not build on x64 out of the box",
                )
            ]
        )(
            PaperConfigSpecificGit(
                project_name="x264",
                remote="https://code.videolan.org/videolan/x264.git",
                local="x264",
                refspec="origin/HEAD",
                limit=None,
                shallow=False,
            )
        ),
        FeatureSource(),
        PatchVariationSource(),
        HTTP(
            local="aspen-1080p.y4m",
            remote={
                "1.0": "https://media.xiph.org/video/derf/y4m/aspen_1080p.y4m"
            },
        ),
        HTTP(
            local="old-town-2160p.y4m",
            remote={
                "1.0": "https://media.xiph.org/video/derf/y4m/old_town_cross_2160p50.y4m"
            },
        ),
        HTTP(
            local="nocturne-1080p.y4m",
            remote={
                "1.0": "https://storage.googleapis.com/downloads.webmproject.org/"
                "AV2Sequences/420_8bit_1080p/"
                "nocturne_aom_sdr_8540-9009_offset2_420_8bit_1080p.y4m"
            },
        ),
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_12)

    WORKLOADS: typing.ClassVar = {
        WorkloadSet(WorkloadCategory.SMALL): [
            VCommand(
                SourceRoot("x264") / RSBinary("x264"),
                ConfigParams(),
                "aspen-1080p.y4m",
                "-o",
                "/dev/null",
                label="aspen-1080p",
            ),
            VCommand(
                SourceRoot("x264") / RSBinary("x264"),
                ConfigParams(),
                "nocturne-1080p.y4m",
                "-o",
                "/dev/null",
                label="nocturne-1080p",
            ),
        ],
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("x264") / RSBinary("x264"),
                ConfigParams(),
                "old-town-2160p.y4m",
                "-o",
                "/dev/null",
                label="old-town-2160p",
            )
        ],
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash,
    ) -> list[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(X264.NAME))

        binary_map.specify_binary("x264", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        x264_repo = get_local_project_repo(self.NAME)
        x264_version_source = local.path(self.source_of_primary)
        x264_version = ShortCommitHash(self.version_of_primary)

        fpic_revisions = get_all_revisions_between(
            x264_repo,
            "5dc0aae2f900064d1f58579929a2285ab289a436",
            "290de9638e5364c37316010ac648a6c959f6dd26",
            ShortCommitHash,
        )
        ldflags_revisions = get_all_revisions_between(
            x264_repo,
            "6490f4398d9e28e65d7517849e729e14eede8c5b",
            "275ef5332dffec445a0c5a78dbc00c3e0766011d",
            ShortCommitHash,
        )

        if x264_version in fpic_revisions:
            self.cflags += ["-fPIC"]

        clang = bb.compiler.cc(self)
        with local.cwd(x264_version_source):
            with local.env(CC=str(clang)):
                configure_flags = ["--disable-asm"]
                if x264_version in ldflags_revisions:
                    configure_flags.append("--extra-ldflags=\"-static\"")
                bb.watch(local["./configure"])(configure_flags)
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    def recompile(self):
        """Recompile the project."""
        x264_version_source = local.path(self.source_of_primary)
        with local.cwd(x264_version_source):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    ##############################
    # SupportsTestSuite Protocol #
    ##############################

    __TEST_SEEDS: tp.ClassVar = [
        0, 42, 1337, 9001, 12345, 54321, 98765, 67890,
        4154874031, 4157556397
    ]

    def prepare_test_environment(self) -> None:
        """Prepare the test environment for this project."""
        self.compile()
        x264_version_source = local.path(self.source_of_primary)

        with local.cwd(x264_version_source):
            bb.watch(make)("checkasm", "-j", get_number_of_jobs(bb_cfg()))

    def build_tests(self) -> None:
        """Build the tests for this project."""
        x264_version_source = local.path(self.source_of_primary)

        with local.cwd(x264_version_source):
            bb.watch(make)("checkasm", "-j", get_number_of_jobs(bb_cfg()))

    def run_testsuite(
            self,
            test_report_path: Path | None = None,
            tests_to_run: tp.Iterable[str] | None = None,
            tests_to_exclude: tp.Iterable[str] | None = None,
    ) -> tp.Optional[tp.Dict[str, TestResult]]:
        x264_version_source = local.path(self.source_of_primary)

        test_results = {}

        with local.cwd(x264_version_source):
            checkasm_8 = local["checkasm8"]
            checkasm_10 = local["checkasm10"]

            for seed in self.__TEST_SEEDS:
                if tests_to_run and f"checkasm8-{seed}" not in tests_to_run:
                    continue

                if tests_to_exclude and f"checkasm8-{seed}" in tests_to_exclude:
                    continue

                _, stdout, _ = bb.watch(checkasm_8)(f"--seed={seed}")

                output = stdout.strip()
                if "All tests passed Yeah :)" in output:
                    test_results[f"checkasm8-{seed}"] = TestResult.PASSED
                else:
                    test_results[f"checkasm8-{seed}"] = TestResult.FAILED

                _, stdout, _ = bb.watch(checkasm_10)(f"--seed={seed}")
                output = stdout.strip()
                if "All tests passed Yeah :)" in output:
                    test_results[f"checkasm10-{seed}"] = TestResult.PASSED
                else:
                    test_results[f"checkasm10-{seed}"] = TestResult.FAILED

        return test_results

    def get_test_names(self) -> tp.Iterable[str]:
        """Get the test names."""
        return ([f"checkasm8-{seed}" for seed in self.__TEST_SEEDS] +
                [f"checkasm10-{seed}" for seed in self.__TEST_SEEDS])