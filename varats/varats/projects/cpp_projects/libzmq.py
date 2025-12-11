"""Project file for zeromq."""
import shutil
import tempfile
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.command import SourceRoot, WorkloadSet
from benchbuild.utils.cmd import make, cmake, mkdir
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.experiment.workload_util import (
    WorkloadCategory,
    RSBinary,
    ConfigParams,
    WorkloadSpecificReportAggregate,
)
from varats.paper.paper_config import PaperConfigSpecificGit
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
from varats.report.multi_patch_report import MultiPatchReport
from varats.report.report import BaseReport
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg
from varats.utils.testsuite_utils import (
    ctest_get_test_names,
    ctest_run_testsuite,
    TestResult,
)


class Libzmq(VProject):
    """The ZeroMQ lightweight messaging kernel is a library which extends the
    standard socket interfaces with features traditionally provided by
    specialised messaging middleware products."""

    NAME = 'libzmq'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.CPP_LIBRARY

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="libzmq",
            remote="https://github.com/zeromq/libzmq.git",
            local="libzmq_git",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        FeatureSource()
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_12).run(
        'apt', 'install', '-y', 'cmake', 'build-essential', 'gnutls-dev',
        'libsodium-dev', 'pkg-config'
    )

    COUNT_ARGS = [f"{2**x}" for x in range(3, 20)]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("libzmq_git") / RSBinary("inproc_thr"),
                ConfigParams(),
                "10000000",
                label=f"bench-inproc-thr",
                requires_any_args=set(COUNT_ARGS),
            ),
            VCommand(
                SourceRoot("libzmq_git") / RSBinary("inproc_lat"),
                ConfigParams(),
                "1000000",
                label=f"bench-inproc-lat",
                requires_any_args=set(COUNT_ARGS),
            ),
            VCommand(
                SourceRoot("libzmq_git") / RSBinary("benchmark_radix_tree"),
                label="bench-radix-tree",
                requires_all_args={"radix"},
            )
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(Libzmq.NAME))

        binary_map.specify_binary(
            "build/lib/libzmq.so", BinaryType.SHARED_LIBRARY
        )

        binary_map.specify_binary("build/bin/inproc_thr", BinaryType.EXECUTABLE)

        binary_map.specify_binary("build/bin/inproc_lat", BinaryType.EXECUTABLE)

        binary_map.specify_binary(
            "build/bin/benchmark_radix_tree", BinaryType.EXECUTABLE
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        libzmq_version_source = local.path(self.source_of_primary)

        cpp_compiler = bb.compiler.cxx(self)
        cc_compiler = bb.compiler.cc(self)

        mkdir["-p"](libzmq_version_source / "build")
        with local.cwd(libzmq_version_source / "build"):
            with local.env(CXX=str(cpp_compiler), CC=str(cc_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(libzmq_version_source):
            verify_binaries(self)

    def recompile(self) -> None:
        """Recompile the project."""
        libzmq_version_source = local.path(self.source_of_primary)

        with local.cwd(libzmq_version_source / "build"):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Zeromq", "Libzmq")]

    def prepare_test_environment(self) -> None:
        """Prepare the testsuite."""
        version_source = local.path(self.source_of_primary)

        cc_compiler = bb.compiler.cc(self)
        cpp_compiler = bb.compiler.cxx(self)

        mkdir("-p", version_source / "build")

        with local.cwd(version_source / "build"):
            with local.env(CC=str(cc_compiler), CXX=str(cpp_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")

    def build_tests(self) -> None:
        """Build the tests."""
        libzmq_version_source = local.path(self.source_of_primary)

        with local.cwd(libzmq_version_source / "build"):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    def get_test_names(self) -> tp.Iterable[str]:
        """Get the test names."""
        build_dir = local.path(self.source_of_primary) / "build"
        return ctest_get_test_names(build_dir)

    def run_testsuite(
        self,
        test_report_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None,
        tests_to_exclude: tp.Optional[tp.Iterable[str]] = None
    ) -> tp.Optional[tp.Dict[str, TestResult]]:
        """Run the testsuite."""
        build_dir = local.path(self.source_of_primary) / "build"
        return ctest_run_testsuite(
            build_dir, test_report_path, tests_to_run, tests_to_exclude
        )


class LibZMQBenchmarkReport(BaseReport, shorthand="ZBR", file_type=".txt"):
    """LibZMQ benchmark report."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)

        self.__message_size = None
        self.__count = None
        self.__latency = None
        self.__throughput_msg = None
        self.__throughput_mb = None

        with open(path) as f:
            for line in f:
                if "message size" in line:
                    self.__message_size = int(line.split(" ")[2].strip())
                if "count" in line:
                    self.__count = int(line.split(" ")[2].strip())
                if "latency" in line:
                    self.__latency = float(line.split(" ")[2].strip())
                if "throughput" in line and "msg/s" in line:
                    self.__throughput_msg = float(line.split(" ")[2].strip())
                if "throughput" in line and "Mb/s" in line:
                    self.__throughput_mb = float(line.split(" ")[2].strip())

    @property
    def message_size(self) -> int:
        return self.__message_size

    @property
    def count(self) -> int:
        return self.__count

    @property
    def latency(self) -> float:
        return self.__latency

    @property
    def throughput_msg(self) -> float:
        return self.__throughput_msg

    @property
    def throughput_mb(self) -> float:
        return self.__throughput_mb


class LibZMQ_WLAggregate(
    WorkloadSpecificReportAggregate[LibZMQBenchmarkReport],
    shorthand="ZBR_WLA",
    file_type=".zip"
):
    """LibZMQ workload report aggregate."""

    def __init__(self, path: Path) -> None:
        super().__init__(
            path, LibZMQBenchmarkReport, label_method=lambda p: "Default"
        )

        self._latencies: tp.List[float] = [
            report.latency
            for report in self.reports("Default")
            if report.latency is not None
        ]

        self._throughputs_msg: tp.List[float] = [
            report.throughput_msg
            for report in self.reports("Default")
            if report.throughput_msg is not None
        ]

        self._throughputs_mb: tp.List[float] = [
            report.throughput_mb
            for report in self.reports("Default")
            if report.throughput_mb is not None
        ]

    @property
    def latencies(self) -> tp.List[float]:
        return self._latencies

    @property
    def throughputs_msg(self) -> tp.List[float]:
        return self._throughputs_msg

    @property
    def throughputs_mb(self) -> tp.List[float]:
        return self._throughputs_mb


class LibZMQMPReport(
    MultiPatchReport[LibZMQ_WLAggregate], shorthand="ZBR_MPA", file_type=".zip"
):
    """LibZMQ multi-patch report aggregate."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, LibZMQ_WLAggregate)
        self.__patched_reports: tp.Dict[str, LibZMQ_WLAggregate] = {}
        self.__base = None
        self.__bases = []

        with tempfile.TemporaryDirectory() as tmp_result_dir:
            shutil.unpack_archive(path, extract_dir=tmp_result_dir)

            for report in Path(tmp_result_dir).iterdir():
                if self.is_baseline_report(report.name):
                    base_report = LibZMQ_WLAggregate(report)
                    self.__base = base_report
                    self.__bases.append(base_report)
                elif self.is_patched_report(report.name):
                    self.__patched_reports[
                        self._parse_patch_shorthand_from_report_name(
                            report.name
                        )] = LibZMQ_WLAggregate(report)

            if not self.__base or not self.__patched_reports:
                raise AssertionError(
                    f"Reports were missing in the file {path=}"
                )

    def all_baseline_reports(self) -> tp.List[LibZMQ_WLAggregate]:
        return self.__bases
