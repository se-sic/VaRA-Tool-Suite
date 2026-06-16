"""Project file for zeromq."""
import shutil
import tempfile
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.command import SourceRoot, WorkloadSet
from benchbuild.utils.cmd import cmake, make, mkdir
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import ImageBase, get_base_image
from varats.experiment.workload_util import (
    ConfigParams,
    RSBinary,
    WorkloadCategory,
    WorkloadSpecificReportAggregate,
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
from varats.report.multi_patch_report import MultiPatchReport
from varats.report.report import BaseReport
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg
from varats.utils.testsuite_utils import (
    TestResult,
    ctest_get_test_names,
    ctest_run_testsuite,
)

COUNT_ARGS = [f"{2**x}" for x in range(3, 20)]


class Libzmq(VProject):
    """
    ZeroMQ is a lightweight messaging kernel library.

    It extends the
    standard socket interfaces with features traditionally provided by
    specialised messaging middleware products.
    """

    NAME = 'libzmq'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.CPP_LIBRARY

    SOURCE: tp.ClassVar = [
        PaperConfigSpecificGit(
            project_name="libzmq",
            remote="https://github.com/zeromq/libzmq.git",
            local="libzmq_git",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        FeatureSource(),
        PatchVariationSource()
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_12).run(
        'apt', 'install', '-y', 'cmake', 'build-essential', 'gnutls-dev',
        'libsodium-dev', 'pkg-config'
    )

    WORKLOADS: tp.ClassVar = {
        WorkloadSet(WorkloadCategory.EXAMPLE):
            [VCommand(
                SourceRoot("libzmq_git") / RSBinary("inproc_thr"),
                count,
                "10000000",
                label=f"bench-inproc-thr-{count}",
            ) for count in COUNT_ARGS] + [
            VCommand(
                SourceRoot("libzmq_git") / RSBinary("inproc_lat"),
                count,
                "1000000",
                label=f"bench-inproc-lat-{count}",
            ) for count in COUNT_ARGS]  + [
            VCommand(
                SourceRoot("libzmq_git") / RSBinary("benchmark_radix_tree"),
                label="bench-radix-tree",
            )]
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
        self.__trie_lookup_time = None
        self.__radix_tree_time = None

        with open(path) as f:
            # get first line to determine the type of report
            first_line = f.readline()
            if "message size" in first_line:
                # Case for latency and throughput reports
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
            else:
                # Case for radix tree benchmark report
                # Report structure:
                """
                keys = 10000, queries = 1000000, key size = 20
                [trie]
                Average lookup time = 121.0 ns
                [radix_tree]
                Average lookup time = 102.0 ns
                """
                # We ignore meta parameter
                for line in f:
                    if "[trie]" in line:
                        # Next line contains the trie lookup time
                        next_line = f.readline()
                        if "Average lookup time" in next_line:
                            self.__trie_lookup_time = float(
                                next_line.split("=")[1].strip().split(" ")[0]
                            )
                    if "[radix_tree]" in line:
                        # Next line contains the radix tree lookup time
                        next_line = f.readline()
                        if "Average lookup time" in next_line:
                            self.__radix_tree_time = float(
                                next_line.split("=")[1].strip().split(" ")[0]
                            )

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

    @property
    def trie_lookup_time(self) -> float:
        return self.__trie_lookup_time

    @property
    def radix_tree_time(self) -> float:
        return self.__radix_tree_time

class LibZMQWLAggregate(
    WorkloadSpecificReportAggregate[LibZMQBenchmarkReport],
    shorthand="ZBR_WLA",
    file_type=".zip"
):
    """LibZMQ workload report aggregate."""

    def __init__(self, path: Path) -> None:
        super().__init__(
            path, LibZMQBenchmarkReport
        )

        self._metrics = {}

        self._metrics["latency"] = {
            wl: [report.latency
            for report in self.reports(wl)
            if report.latency is not None] for wl in self.workload_names()
        }

        self._metrics["throughput_msg"]: dict[str, list[float]] = {
            wl: [report.throughput_msg
            for report in self.reports(wl)
            if report.throughput_msg is not None] for wl in self.workload_names()
        }

        self._metrics["throughput_mb"]: dict[str, list[float]] = {
            wl: [report.throughput_mb
            for report in self.reports(wl)
            if report.throughput_mb is not None] for wl in self.workload_names()
        }

        self._metrics["trie_lookup_time"]: dict[str, list[float]] = {
            wl: [report.trie_lookup_time
            for report in self.reports(wl)
            if report.trie_lookup_time is not None] for wl in self.workload_names()
        }

        self._metrics["radix_tree_time"]: dict[str, list[float]] = {
            wl: [report.radix_tree_time
            for report in self.reports(wl)
            if report.radix_tree_time is not None] for wl in self.workload_names()
        }

    @property
    def latencies(self) -> dict[str, list[float]]:
        return self._metrics["latency"]

    @property
    def throughputs_msg(self) -> dict[str, list[float]]:
        return self._metrics["throughput_msg"]

    @property
    def throughputs_mb(self) -> dict[str, list[float]]:
        return self._metrics["throughput_mb"]

    @property
    def trie_lookup_times(self) -> dict[str, list[float]]:
        return self._metrics["trie_lookup_time"]

    @property
    def radix_tree_times(self) -> dict[str, list[float]]:
        return self._metrics["radix_tree_time"]

    @property
    def metrics(self) -> dict[str, dict[str, list[float]]]:
        return self._metrics


class LibZMQMPReport(
    MultiPatchReport[LibZMQWLAggregate], shorthand="ZBR_MPA", file_type=".zip"
):
    """LibZMQ multi-patch report aggregate."""

    @staticmethod
    def _parse_binary_name_from_baseline_report_name(file_name: str) -> str:
        # Baseline report name structure: baseline_{binary_name}.zip
        if file_name.endswith(".zip"):
            file_name.strip(".zip")
        return file_name[len("baseline_"):]

    @staticmethod
    def _parse_binary_name_from_patched_report_name(file_name: str) -> str:
        # Patched report name structure: patched_{patch_shortname_length}_{patch_shortname}_{binary_name}.zip
        if file_name.endswith(".zip"):
            file_name.strip(".zip")
        fn_without_prefix = file_name[len("patched_"):]
        split_leftover_fn = fn_without_prefix.partition("_")
        shortname_length = int(split_leftover_fn[0])
        return "".join(split_leftover_fn[2:])[shortname_length + 1:]

    def __init__(self, path: Path) -> None:
        super().__init__(path, LibZMQWLAggregate)
        self.__patched_reports: tp.Dict[str, LibZMQWLAggregate] = {}
        self.__base = None
        self.__base_by_binary: dict[str, LibZMQWLAggregate] = {}
        self.__patched_reports_by_binary: dict[str, dict[str, LibZMQWLAggregate]] = {}

        with tempfile.TemporaryDirectory() as tmp_result_dir:
            shutil.unpack_archive(path, extract_dir=tmp_result_dir)

            for report in Path(tmp_result_dir).iterdir():
                if self.is_baseline_report(report.name):
                    base_report = LibZMQWLAggregate(report)
                    self.__base = base_report
                    self.__base_by_binary[
                        self._parse_binary_name_from_baseline_report_name(
                            report.name
                        )] = base_report
                elif self.is_patched_report(report.name):
                    binary_name = self._parse_binary_name_from_patched_report_name(
                        report.name
                    )
                    patch_shortname = self._parse_patch_shorthand_from_report_name(
                        report.name
                    )
                    self.__patched_reports[
                        patch_shortname
                    ] = LibZMQWLAggregate(report)
                    if binary_name not in self.__patched_reports_by_binary:
                        self.__patched_reports_by_binary[binary_name] = {}
                    self.__patched_reports_by_binary[binary_name][
                        patch_shortname
                    ] = LibZMQWLAggregate(report)

            if not self.__base or not self.__patched_reports:
                raise AssertionError(
                    f"Reports were missing in the file {path=}"
                )

    @property
    def binaries(self) -> tp.Collection[str]:
        return self.__base_by_binary.keys()

    def baseline(self, binary_name: str) -> LibZMQWLAggregate:
        return self.__base_by_binary[binary_name]

    def patched(self, binary_name: str, patch_shortname: str) -> LibZMQWLAggregate:
        return self.__patched_reports_by_binary[binary_name][patch_shortname]
