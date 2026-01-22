"""Project file for x264."""
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.command import SourceRoot, WorkloadSet
from benchbuild.utils.cmd import make
from benchbuild.utils.revision_ranges import block_revisions, GoodBadSubgraph
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.experiment.workload_util import RSBinary, WorkloadCategory
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    get_local_project_repo,
    BinaryType,
    verify_binaries,
    RevisionBinaryMap,
    HTTP7z,
)
from varats.project.varats_project import VProject, VCommand
from varats.utils.git_util import ShortCommitHash, get_all_revisions_between
from varats.utils.settings import bb_cfg
from varats.utils.testsuite_utils import (
    ctest_run_testsuite,
    ctest_get_test_names,
    TestResult,
)


class X264(VProject):
    """Video encoder x264 (fetched by Git)"""

    NAME = 'x264'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.CODEC

    SOURCE = [
        block_revisions([
            GoodBadSubgraph(["5dc0aae2f900064d1f58579929a2285ab289a436"],
                            ["6490f4398d9e28e65d7517849e729e14eede8c5b"],
                            "Does not build on x64 out of the box")
        ])(
            PaperConfigSpecificGit(
                project_name="x264",
                remote="https://code.videolan.org/videolan/x264.git",
                local="x264",
                refspec="origin/HEAD",
                limit=None,
                shallow=False
            )
        ),
        HTTP7z(
            local="Bosphorus_1920x1080_120fps_420_8bit_YUV_Y4M",
            remote={
                "1.0":
                    "http://ultravideo.cs.tut.fi/video/"
                    "Bosphorus_1920x1080_120fps_420_8bit_YUV_Y4M.7z"
            }
        ),
        HTTP7z(
            local="Bosphorus_3840x2160_120fps_420_8bit_YUV_Y4M",
            remote={
                "1.0":
                    "http://ultravideo.cs.tut.fi/video/"
                    "Bosphorus_3840x2160_120fps_420_8bit_YUV_Y4M.7z"
            }
        ),
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("x264") / RSBinary("x264"),
                "--preset medium",
                "--crf 24",
                "--frames 300",
                "--threads auto",
                # Use output_param to ensure input file
                # gets appended after all arguments.
                output_param=["{output}"],
                output=SourceRoot(
                    "Bosphorus_1920x1080_120fps_420_8bit_YUV_Y4M/Bosphorus_1920x1080_120fps_420_8bit_YUV_Y4M.y4m"
                ),
                label="1080-medium-preset",
                creates=[
                    "Bosphorus_1920x1080_120fps_420_8bit_YUV_Y4M/Bosphorus_1920x1080_120fps_420_8bit_YUV_Y4M.y4m"
                ]
            )
        ]
    }

    CONTAINER = get_base_image(ImageBase.DEBIAN_12)

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
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

    def prepare_test_environment(self) -> None:
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

    def get_test_names(self) -> tp.Iterable[str]:
        pass

    def build_tests(self) -> None:
        x264_version_source = local.path(self.source_of_primary)

        with local.cwd(x264_version_source):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    def run_testsuite(
        self,
        test_report_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None,
        tests_to_exclude: tp.Optional[tp.Iterable[str]] = None
    ) -> tp.Optional[tp.Dict[str, TestResult]]:
        pass


# http://www.phoronix-test-suite.com/benchmark-files/x264-git-20220222.tar.bz2 700 ish kb
# http://ultravideo.cs.tut.fi/video/Bosphorus_1920x1080_120fps_420_8bit_YUV_Y4M.7z 670 mb
# http://ultravideo.cs.tut.fi/video/Bosphorus_3840x2160_120fps_420_8bit_YUV_Y4M.7z 2.8 gb
