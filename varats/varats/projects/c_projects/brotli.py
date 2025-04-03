"""Project file for brotli."""
import json
import typing as tp
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

    CONTAINER = get_base_image(ImageBase.DEBIAN_10
                              ).run('apt', 'install', '-y', 'cmake')

    def __get_build_dir(self) -> Path:
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

        if brotli_version in simple_make_revisions:
            run_dir = brotli_version_source / "tools"
        elif brotli_version in configure_revisions:
            run_dir = brotli_version_source
        else:
            run_dir = brotli_version_source / "out"

        return run_dir

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

    def run_testsuite(
        self,
        test_report_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None
    ) -> bool:
        # TODO: Partial test suite
        run_dir = self.__get_build_dir()

        with local.cwd(run_dir):
            test_command = make["test", "-j", get_number_of_jobs(bb_cfg())]
            ret_code, test_output, _ = bb.watch(test_command)()

        if test_report_path:
            with open(test_report_path, "w") as file:
                file.write(test_output)

        return ret_code == 0

    def get_test_names(self) -> tp.Iterable[str]:
        run_dir = self.__get_build_dir()

        ctest_cmd = ctest["--show-only=json-v1"]

        try:
            with local.cwd(run_dir):
                _, output, _ = bb.watch(ctest_cmd)
        except ProcessExecutionError:
            return []

        test_info = json.loads(output)

        return [test["name"] for test in test_info["tests"]]

    def compile(self) -> None:
        """Compile the project."""
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
        c_compiler = bb.compiler.cc(self)

        if brotli_version in simple_make_revisions:
            with local.cwd(brotli_version_source / "tools"):
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
        elif brotli_version in configure_revisions:
            with local.cwd(brotli_version_source):
                with local.env(CC=str(c_compiler)):
                    bb.watch(local["./configure"])()
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
        else:
            mkdir(brotli_version_source / "out")
            with local.cwd(brotli_version_source / "out"):
                with local.env(CC=str(c_compiler)):
                    bb.watch(cmake)("-G", "Unix Makefiles", "..")
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(brotli_version_source):
            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("google", "brotli")]
