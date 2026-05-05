"""Project file for lrzip."""
import typing as tp
from functools import partial  # , Placeholder - Not yet supported on Debian 12
from pathlib import Path

import benchbuild as bb
from benchbuild.command import SourceRoot, WorkloadSet
from benchbuild.source import HTTPMultiple
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local, ProcessExecutionError

from varats.containers.containers import get_base_image, ImageBase
from varats.experiment.workload_util import (
    RSBinary,
    WorkloadCategory,
    ConfigParams,
)
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.patch_variation_source import PatchVariationSource
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_repo,
    verify_binaries,
    RevisionBinaryMap,
)
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg
from varats.utils.testsuite_utils import TestResult, compression_end_to_end


class Lrzip(VProject):
    """Compression and decompression tool lrzip (fetched by Git)"""

    __SOURCE_FILES = [
        "countries-land-1m.geo.json", "countries-land-10m.geo.json",
        "countries-land-100m.geo.json", "countries-land-10km.geo.json",
        "countries-land-1km.geo.json", "countries-land-250m.geo.json",
        "countries-land-25m.geo.json", "countries-land-2km5.geo.json",
        "countries-land-2m5.geo.json", "countries-land-500m.geo.json",
        "countries-land-50m.geo.json", "countries-land-5km.geo.json",
        "countries-land-5m.geo.json"
    ]

    NAME = 'lrzip'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.COMPRESSION

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="lrzip",
            remote="https://github.com/ckolivas/lrzip.git",
            local="lrzip",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        PatchVariationSource(),
        # TODO: auto unzipper for BB?
        HTTPMultiple(
            local="geo-maps",
            remote={
                "1.0":
                    "https://github.com/simonepri/geo-maps/releases/"
                    "download/v0.6.0"
            },
            files=__SOURCE_FILES
        ),
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_12).run(
        'apt', 'install', '-y', 'tar', 'libz-dev', 'autoconf', 'libbz2-dev',
        'liblzo2-dev', 'liblz4-dev', 'coreutils', 'libtool'
    )

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.SMALL): [
            VCommand(
                SourceRoot("lrzip") / RSBinary("lrzip"),
                ConfigParams(),
                "-f",
                "geo-maps/countries-land-1km.geo.json",
                label="countries-land-1km",
                creates=["countries-land-1km.geo.json.lrz"]
            ),
            VCommand(
                SourceRoot("lrzip") / RSBinary("lrzip"),
                ConfigParams(),
                "-f",
                "geo-maps/countries-land-100m.geo.json",
                label="countries-land-100m",
                creates=["countries-land-100m.geo.json.lrz"]
            )
        ],
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("lrzip") / RSBinary("lrzip"),
                ConfigParams(),
                "-f",
                "geo-maps/countries-land-10m.geo.json",
                label="countries-land-10m",
                creates=["countries-land-10m.geo.json.lrz"]
            ),
        ],
        WorkloadSet(WorkloadCategory.LARGE): [
            VCommand(
                SourceRoot("lrzip") / RSBinary("lrzip"),
                ConfigParams(),
                "-f",
                "geo-maps/countries-land-1m.geo.json",
                label="countries-land-1m",
                creates=["countries-land-1m.geo.json.lrz"]
            ),
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(Lrzip.NAME))

        binary_map.specify_binary("lrzip", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        lrzip_source = local.path(self.source_of_primary)

        self.cflags += ["-fPIC"]

        cc_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        with local.cwd(lrzip_source):
            with local.env(CC=str(cc_compiler), CXX=str(cxx_compiler)):
                bb.watch(local["./autogen.sh"])()
                bb.watch(local["./configure"])()
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    def recompile(self):
        lrzip_source = local.path(self.source_of_primary)

        with local.cwd(lrzip_source):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("lrzip_project", "lrzip")]

    ##############################
    # SupportTestSuites Protocol #
    ##############################

    def prepare_test_environment(self) -> None:
        # Nothing required
        pass

    def build_tests(self) -> None:
        self.compile()

    def run_testsuite(
        self,
        test_report_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None,
        tests_to_exclude: tp.Optional[tp.Iterable[str]] = None
    ) -> tp.Optional[tp.Dict[str, TestResult]]:

        if tests_to_run is None:
            tests_to_run = self.get_test_names()

        tests_to_run = set(tests_to_run)

        if tests_to_exclude is not None:
            tests_to_run = tests_to_run.difference(set(tests_to_exclude))

        # Resolve test names to files
        test_files = [
            Path("geo-maps").absolute() / f"{test_name}.geo.json"
            for test_name in tests_to_run
        ]

        lrzip_bin = self.binaries[0]
        lrzip_cmd = local[f"lrzip/{lrzip_bin.path}"]

        #decompression_cmd = partial(lrzip_cmd, "-d", Placeholder, "--out", Placeholder)

        test_results = {}

        for file in test_files:
            print("Running end-to-end test for", file)
            test_name = file.stem.removesuffix(".geo")
            test_status = TestResult.UNKNOWN

            compressed_file = file.with_suffix(file.suffix + ".compressed")
            decompressed_file = file.with_suffix(file.suffix + ".decompressed")

            try:
                bb.watch(lrzip_cmd)(file, "--outfile", compressed_file)
            except:
                print("Error during compression of", file)
                test_status = TestResult.FAILED
                test_results[test_name] = test_status
                continue

            # Decompress the file
            try:
                bb.watch(lrzip_cmd)(
                    "-d", compressed_file, "--outfile", decompressed_file
                )
            except:
                print("Error during decompression of", compressed_file)
                test_status = TestResult.FAILED
                test_results[test_name] = test_status
                continue

            # Check if the original file is restored correctly
            if file.read_bytes() == decompressed_file.read_bytes():
                test_status = TestResult.PASSED
            else:
                print("Decompressed file does not match original for", file)
                test_status = TestResult.FAILED

            test_results[test_name] = test_status

            # Cleanup
            compressed_file.unlink(missing_ok=True)
            decompressed_file.unlink(missing_ok=True)

        return test_results

    def get_test_names(self) -> tp.List[str]:
        return [t.removesuffix(".geo.json") for t in self.__SOURCE_FILES]
