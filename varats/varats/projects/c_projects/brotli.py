"""Project file for brotli."""
import json
import re
import typing as tp
from enum import Enum
from pathlib import Path

from benchbuild.utils.cmd import cmake, mkdir, make, ctest
from benchbuild.utils.revision_ranges import (
    RevisionRange,
    block_revisions,
    SingleRevision,
)
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local, ProcessExecutionError

import benchbuild as bb
from varats.containers.containers import get_base_image, ImageBase
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_repo,
    verify_binaries,
    RevisionBinaryMap,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, get_all_revisions_between
from varats.utils.settings import bb_cfg


class Brotli(VProject):
    """Brotli compression format."""

    NAME = 'brotli'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.COMPRESSION

    SOURCE = [
        block_revisions([
            RevisionRange(
                '8f30907d0f2ef354c2b31bdee340c2b11dda0fb0',
                'e1739826c04a9944672b99b98249dda021bdeb36',
                'Encoder and Decoder don\'t have a shared Makefile'
            ),
            SingleRevision(
                "378485b097fd7b80a5e404a3cb912f7b18f78cdb",
                "Missing required build files"
            )
        ])(
            PaperConfigSpecificGit(
                project_name="brotli",
                remote="https://github.com/google/brotli.git",
                local="brotli_git",
                refspec="origin/HEAD",
                limit=None,
                shallow=False
            )
        )
    ]

    class BrotliBuildMethod(Enum):
        MAKE = 0
        CONFIGURE = 1
        CMAKE = 2

    CONTAINER = get_base_image(ImageBase.DEBIAN_10
                              ).run('apt', 'install', '-y', 'cmake')

    def __get_build_dir(self) -> tp.Tuple[Path, BrotliBuildMethod]:
        """Get the build directory and the build method."""
        brotli_version_source = local.path(self.source_of_primary)
        brotli_repo = get_local_project_repo(self.NAME)
        brotli_version = ShortCommitHash(self.version_of_primary)
        configure_revisions = get_all_revisions_between(
            brotli_repo, "f9ab24a7aaee93d5932ba212e5e3d32e4306f748",
            "5814438791fb2d4394b46e5682a96b68cd092803", ShortCommitHash
        )
        simple_make_revisions = get_all_revisions_between(
            brotli_repo, "e1739826c04a9944672b99b98249dda021bdeb36",
            "378485b097fd7b80a5e404a3cb912f7b18f78cdb", ShortCommitHash
        )
        run_dir: Path
        build_method: Brotli.BrotliBuildMethod
        if brotli_version in simple_make_revisions:
            run_dir = brotli_version_source / "tools"
            build_method = Brotli.BrotliBuildMethod.MAKE
        elif brotli_version in configure_revisions:
            build_method = Brotli.BrotliBuildMethod.CONFIGURE
            run_dir = brotli_version_source
        else:
            build_method = Brotli.BrotliBuildMethod.CMAKE
            run_dir = brotli_version_source / "out"

        return run_dir, build_method

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(Brotli.NAME))

        binary_map.specify_binary(
            "out/brotli",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange(
                "03739d2b113afe60638069c4e1604dc2ac27380d", "HEAD"
            )
        )
        binary_map.specify_binary(
            "out/bro",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange(
                "5814438791fb2d4394b46e5682a96b68cd092803",
                "03739d2b113afe60638069c4e1604dc2ac27380d"
            )
        )
        binary_map.specify_binary(
            "bin/bro",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange(
                "f9ab24a7aaee93d5932ba212e5e3d32e4306f748",
                "5814438791fb2d4394b46e5682a96b68cd092803"
            )
        )
        binary_map.specify_binary(
            "tools/bro",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange(
                "e1739826c04a9944672b99b98249dda021bdeb36",
                "378485b097fd7b80a5e404a3cb912f7b18f78cdb"
            )
        )
        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def prepare_testsuite(self):
        build_dir, method = self.__get_build_dir()
        if method != Brotli.BrotliBuildMethod.CMAKE:
            # Currently unsupported/untested how to run the tests
            raise NotImplementedError(
                "Test suites are not supported for this revision of brotli as it does not use CMake."
            )
        with local.cwd(build_dir):
            # Prepare the build directory
            bb.watch(cmake["..", "-G", "Unix Makefiles"])()

            # Build the test suite
            bb.watch(make["-j", get_number_of_jobs(bb_cfg())])()

    def get_test_names(self) -> tp.Iterable[str]:
        """Get the test names for the project."""

        build_dir, method = self.__get_build_dir()
        if method != Brotli.BrotliBuildMethod.CMAKE:
            raise NotImplementedError(
                "Test suites are not supported for this revision of brotli as it does not use CMake."
            )

        ctest_cmd = ctest["--show-only=json-v1"]

        try:
            with local.cwd(build_dir):
                _, output, _ = bb.watch(ctest_cmd)
        except ProcessExecutionError:
            return []

        test_info = json.loads(output)

        return [test["name"] for test in test_info["tests"]]

    def run_testsuite(
        self,
        test_report_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None
    ) -> bool:
        build_dir, method = self.__get_build_dir()

        if method != Brotli.BrotliBuildMethod.CMAKE:
            raise NotImplementedError(
                "Test suites are not supported for this revision of brotli as it does not use CMake."
            )

        with local.cwd(build_dir):
            ctest_cmd = ctest
            if test_report_path:
                ctest_cmd = ctest_cmd["--output-junit", test_report_path]

            if tests_to_run:
                test_regex = f"^{'|'.join([re.escape(name) for name in tests_to_run])}''$"

                ctest_cmd = ctest_cmd["-R", test_regex]

            ret_code, _, _ = bb.watch(ctest_cmd)()

        return ret_code == 0

    def compile(self) -> None:
        """Compile the project."""
        brotli_version_source = local.path(self.source_of_primary)
        c_compiler = bb.compiler.cc(self)

        build_dir, method = self.__get_build_dir()

        with local.cwd(build_dir):
            with local.env(CC=str(c_compiler)):
                match method:
                    case Brotli.BrotliBuildMethod.MAKE:
                        # No special setup required
                        pass
                    case Brotli.BrotliBuildMethod.CONFIGURE:
                        bb.watch(local["./configure"])()
                    case Brotli.BrotliBuildMethod.CMAKE:
                        bb.watch(cmake)("-G", "Unix Makefiles", "..")

                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(brotli_version_source):
            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("google", "brotli")]
