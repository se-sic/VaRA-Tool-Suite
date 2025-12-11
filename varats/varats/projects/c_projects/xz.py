"""Project file for xz."""
import typing as tp
from pathlib import Path
from typing import Iterable

import benchbuild as bb
from benchbuild.command import SourceRoot, WorkloadSet
from benchbuild.source import HTTPMultiple
from benchbuild.utils.cmd import autoreconf, make, ninja
from benchbuild.utils.revision_ranges import (
    block_revisions,
    GoodBadSubgraph,
    RevisionRange,
)
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
)
from varats.project.sources import FeatureSource
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, get_all_revisions_between
from varats.utils.settings import bb_cfg
from varats.utils.testsuite_utils import (
    ctest_get_test_names,
    ctest_run_testsuite,
    TestResult,
)


class Xz(VProject):
    """Compression and decompression tool xz (fetched by Git)"""

    NAME = 'xz'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.COMPRESSION

    SOURCE = [
        block_revisions([
            GoodBadSubgraph(["cf49f42a6bd40143f54a6b10d6e605599e958c0b"],
                            ["4c7ad179c78f97f68ad548cb40a9dfa6871655ae"],
                            "missing file api/lzma/easy.h"),
            GoodBadSubgraph(["335fe260a81f61ec99ff5940df733b4c50aedb7c"],
                            ["24e0406c0fb7494d2037dec033686faf1bf67068"],
                            "use of undeclared LZMA_THREADS_MAX"),
            RevisionRange(
                "5d018dc03549c1ee4958364712fb0c94e1bf2741",
                "c324325f9f13cdeb92153c5d00962341ba070ca2",
                "Initial git import without xz"
            )
        ])(
            PaperConfigSpecificGit(
                project_name='xz',
                remote="https://github.com/tukaani-project/xz",
                local="xz",
                refspec="origin/HEAD",
                limit=None,
                shallow=False
            )
        ),
        FeatureSource(),
        HTTPMultiple(
            local="geo-maps",
            remote={
                "1.0":
                    "https://github.com/simonepri/geo-maps/releases/"
                    "download/v0.6.0"
            },
            files=[
                "countries-land-1km.geo.json", "countries-land-250m.geo.json",
                "countries-land-10m.geo.json"
            ]
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', 'autoconf', 'autopoint', 'automake',
        'autotools-dev', 'libtool', 'pkg-config'
    )

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("xz") / RSBinary("xz"),
                "-f",
                "-k",
                "geo-maps/countries-land-1km.geo.json",
                label="countries-land-1km",
                creates=["geo-maps/countries-land-1km.geo.json.xz"]
            )
        ],
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("xz") / RSBinary("xz"),
                "-f",
                "-k",
                "-9e",
                "--compress",
                "--threads=1",
                "--format=xz",
                "-vv",
                "geo-maps/countries-land-250m.geo.json",
                label="countries-land-250m",
                creates=["geo-maps/countries-land-250m.geo.json.xz"],
                requires_all_args={"--compress"},
            )
        ],
        WorkloadSet(WorkloadCategory.LARGE): [
            VCommand(
                SourceRoot("xz") / RSBinary("xz"),
                "-f",
                "-k",
                "-9e",
                "--compress",
                "--threads=1",
                "--format=xz",
                "-vv",
                "geo-maps/countries-land-10m.geo.json",
                label="countries-land-10m",
                creates=["geo-maps/countries-land-10m.geo.json.xz"],
            )
        ],
    }

    def __init__(self, revision):
        super().__init__(revision)
        xz_repo = get_local_project_repo(self.NAME)
        self._CMAKE_VERSIONS = get_all_revisions_between(
            xz_repo, "8d26b72915e0d373f898b55935505857c30dbdb3", "HEAD",
            ShortCommitHash
        )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(Xz.NAME))

        binary_map.specify_binary(
            'src/xz/xz',
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("5d018dc035", "3f86532407")
        )

        binary_map.specify_binary(
            'src/xz/.libs/xz',
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("880c330938", "32412bd2a4")
        )

        binary_map.specify_binary(
            'build/xz',
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("8d26b72915", "HEAD")
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        xz_repo = get_local_project_repo(self.NAME)
        xz_version_source = local.path(self.source_of_primary)
        xz_version = ShortCommitHash(self.version_of_primary)

        # dynamic linking is off by default until
        # commit f9907503f882a745dce9d84c2968f6c175ba966a
        # (fda4724 is its parent)
        revisions_wo_dynamic_linking = get_all_revisions_between(
            xz_repo, "5d018dc03549c1ee4958364712fb0c94e1bf2741",
            "fda4724d8114fccfa31c1839c15479f350c2fb4c", ShortCommitHash
        )

        self.cflags += ["-fPIC"]

        clang = bb.compiler.cc(self)

        print(f"{xz_version=}")
        print(f"{self._CMAKE_VERSIONS=}")

        if xz_version in self._CMAKE_VERSIONS:
            print("Using CMake build system for xz at revision ")
            build_dir = xz_version_source / "build"
            local["mkdir"]("-p", build_dir)
            with local.cwd(build_dir):
                with local.env(CC=str(clang)):
                    cmake = local["cmake"]
                    cmake("..", "-G", "Ninja")

                bb.watch(ninja)()

            with local.cwd(xz_version_source):
                verify_binaries(self)
        else:
            print("Using Autotools build system for xz at revision ")
            with local.cwd(xz_version_source):
                with local.env(CC=str(clang)):
                    bb.watch(autoreconf)("--install")
                    configure = bb.watch(local["./configure"])

                    if xz_version in revisions_wo_dynamic_linking:
                        configure("--enable-dynamic=yes")
                    else:
                        configure()

                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

                verify_binaries(self)

    def recompile(self):
        xz_version_source = local.path(self.source_of_primary)
        with local.cwd(xz_version_source):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("tukaani", "xz")]

    # TestSuite protocol
    def prepare_test_environment(self) -> None:
        xz_version = ShortCommitHash(self.version_of_primary)
        xz_version_source = local.path(self.source_of_primary)

        if xz_version not in self._CMAKE_VERSIONS:
            raise NotImplementedError(
                "Testsuite protocol is currently only implemented for "
                "CMake based builds."
            )

        clang = bb.compiler.cc(self)

        build_dir = xz_version_source / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        with local.cwd(build_dir):
            with local.env(CC=str(clang)):
                cmake = local["cmake"]
                cmake("..", "-G", "Ninja")

    def build_tests(self) -> None:
        build_dir = local.path(self.source_of_primary) / "build"

        with local.cwd(build_dir):
            # No specific target for tests, so just build everything
            bb.watch(ninja)()

    def run_testsuite(
        self,
        test_report_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None,
        tests_to_exclude: tp.Optional[tp.Iterable[str]] = None
    ) -> tp.Optional[tp.Dict[str, TestResult]]:
        build_dir = local.path(self.source_of_primary) / "build"

        return ctest_run_testsuite(
            build_dir,
            test_report_path=test_report_path,
            tests_to_run=tests_to_run,
            tests_to_exclude=tests_to_exclude
        )

    def get_test_names(self) -> Iterable[str]:
        build_dir = local.path(self.source_of_primary) / "build"
        return ctest_get_test_names(build_dir)
