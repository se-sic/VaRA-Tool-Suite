import json
import shutil
import tempfile
import typing as tp
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import xmltodict
from frozendict import frozendict

from varats.report.multi_patch_report import MultiPatchReport
from varats.report.report import BaseReport, ReportAggregate, ReportFilename


@dataclass
class BenchbaseLatencies:
    max_latency: int
    min_latency: int
    median_latency: int
    average_latency: int
    percentile_25: int
    percentile_75: int
    percentile_90: int
    percentile_95: int
    percentile_99: int


@dataclass
class BenchbaseResultSummary:
    benchbase_config: tp.Dict
    dbms_type: str
    benchmark: str
    latencies: BenchbaseLatencies
    throughput: float
    goodput: float
    scale_factor: float
    terminals: int
    num_requests: int


@dataclass
class BenchbaseFullResult:
    summary: BenchbaseResultSummary
    raw_requests: pd.DataFrame
    sampled_metrics: pd.DataFrame
    samples_metrics_by_category: tp.Dict[str, pd.DataFrame]
    raw_samples: pd.DataFrame


class BenchBaseReport(BaseReport, shorthand="BBR", file_type="zip"):
    """Class representing a report for BenchBase benchmarks."""

    def _load_report_data(self) -> None:
        # Open zip file and pares report data
        self.__results: tp.Dict[str, BenchbaseFullResult] = {}
        with zipfile.ZipFile(self.path, 'r') as zip_ref:
            # Extract the different benchbase runs
            # Each benchbase run creates multiple files, which can be distinguished by their prefixes
            # For example: <workload>_<datetime>.<suffixes>
            file_list = zip_ref.namelist()

            workloads = {name.split('.')[0] for name in file_list}
            counts = {
                run:
                    sum(
                        1
                        for name in workloads
                        if name.startswith(run.split('_', 1)[0])
                    ) for run in workloads
            }

            for workload in workloads:
                with zip_ref.open(f"{workload}.config.xml") as config_file:
                    config = xmltodict.parse(config_file.read())

                # Load summary data
                with zip_ref.open(f"{workload}.summary.json") as summary_file:
                    summary_json = json.load(summary_file)

                    latencies = BenchbaseLatencies(
                        max_latency=summary_json['Latency Distribution']
                        ['Maximum Latency (microseconds)'],
                        min_latency=summary_json['Latency Distribution']
                        ['Minimum Latency (microseconds)'],
                        median_latency=summary_json['Latency Distribution']
                        ['Median Latency (microseconds)'],
                        average_latency=summary_json['Latency Distribution']
                        ['Average Latency (microseconds)'],
                        percentile_25=summary_json['Latency Distribution']
                        ['25th Percentile Latency (microseconds)'],
                        percentile_75=summary_json['Latency Distribution']
                        ['75th Percentile Latency (microseconds)'],
                        percentile_90=summary_json['Latency Distribution']
                        ['90th Percentile Latency (microseconds)'],
                        percentile_95=summary_json['Latency Distribution']
                        ['95th Percentile Latency (microseconds)'],
                        percentile_99=summary_json['Latency Distribution']
                        ['99th Percentile Latency (microseconds)'],
                    )

                    summary = BenchbaseResultSummary(
                        benchbase_config=config,
                        dbms_type=summary_json['DBMS Type'],
                        benchmark=summary_json['Benchmark Type'],
                        latencies=latencies,
                        throughput=summary_json['Throughput (requests/second)'],
                        goodput=summary_json['Goodput (requests/second)'],
                        scale_factor=summary_json['scalefactor'],
                        terminals=summary_json['terminals'],
                        num_requests=summary_json['Measured Requests'],
                    )

                # Load raw results
                with zip_ref.open(f"{workload}.raw.csv") as raw_results_file:
                    raw_results_df = pd.read_csv(raw_results_file)

                # Load sampled metrics
                with zip_ref.open(
                    f"{workload}.results.csv"
                ) as sampled_metrics_file:
                    sampled_metrics_df = pd.read_csv(sampled_metrics_file)

                # Load samples metrics by category
                # File name format: <workload>.results.<category>.csv
                samples_metrics_by_category = {}
                for file_name in file_list:
                    if (
                        not file_name.startswith(f"{workload}.results.") or
                        not file_name.endswith(".csv") or
                        file_name == f"{workload}.results.csv"
                    ):
                        continue

                    category = file_name[
                        len(f"{workload}.results."):-len(".csv")]
                    with zip_ref.open(file_name) as category_file:
                        category_df = pd.read_csv(category_file)
                        samples_metrics_by_category[category] = category_df

                # Load raw samples
                with zip_ref.open(
                    f"{workload}.samples.csv"
                ) as raw_samples_file:
                    raw_samples_df = pd.read_csv(raw_samples_file)

                # Create BenchbaseFullResult and store it
                full_result = BenchbaseFullResult(
                    summary=summary,
                    raw_requests=raw_results_df,
                    sampled_metrics=sampled_metrics_df,
                    samples_metrics_by_category=samples_metrics_by_category,
                    raw_samples=raw_samples_df
                )

                key = workload.split("_"
                                    )[0] if counts[workload] == 1 else workload
                self.__results[key] = full_result

    def __init__(self, path: Path):
        super().__init__(path)

        # Load and parse the BenchBase report data from the zip file
        self._load_report_data()

    @property
    def workloads(self) -> tp.KeysView[str]:
        """Get the list of workloads present in the report."""
        return self.__results.keys()

    @property
    def results(self) -> tp.Dict[str, BenchbaseFullResult]:
        """Get the parsed BenchBase results."""
        return self.__results

    def result_for_workload(self,
                            workload: str) -> tp.Optional[BenchbaseFullResult]:
        """Get the BenchBase result for a specific workload."""
        return self.__results.get(workload, None)

    @property
    def summaries(self) -> tp.Dict[str, BenchbaseResultSummary]:
        """Get the summaries of all BenchBase results."""
        return {key: result.summary for key, result in self.__results.items()}

    def summary_for_workload(
        self, workload: str
    ) -> tp.Optional[BenchbaseResultSummary]:
        """Get the summary for a specific workload."""
        result = self.__results.get(workload, None)
        return result.summary if result else None


@dataclass(eq=True, frozen=True)
class BenchbaseResultsIdentifier:
    dbms_type: str
    benchmark: str
    scale_factor: float
    terminals: int


@dataclass
class BenchbaseResultRepsSummary:
    id: BenchbaseResultsIdentifier
    latencies: tp.List[BenchbaseLatencies]
    throughput: tp.List[float]
    goodput: tp.List[float]
    num_requests: tp.List[int]


class BenchBaseReportAggregate(
    BaseReport,
    shorthand=BenchBaseReport.SHORTHAND + ReportAggregate.SHORTHAND,
    file_type=ReportAggregate.FILE_TYPE
):
    """
    Aggregate multiple BenchBase runs in the same zip file into one report.

    Essentially a wrapper around a single BenchBaseReport, but identifies runs
    with same parameters and allows access to aggregated results as repetitions
    """

    def __init__(self, path: Path):
        super().__init__(path)

        bb_report = BenchBaseReport(path)
        self.__summaries: tp.Dict[BenchbaseResultsIdentifier,
                                  BenchbaseResultRepsSummary] = {}

        for _, summary in bb_report.summaries.items():
            identifier = BenchbaseResultsIdentifier(
                dbms_type=summary.dbms_type,
                benchmark=summary.benchmark,
                scale_factor=summary.scale_factor,
                terminals=summary.terminals
            )

            if identifier not in self.__summaries:
                self.__summaries[identifier] = BenchbaseResultRepsSummary(
                    id=identifier,
                    latencies=[],
                    throughput=[],
                    goodput=[],
                    num_requests=[]
                )

            self.__summaries[identifier].latencies.append(summary.latencies)
            self.__summaries[identifier].throughput.append(summary.throughput)
            self.__summaries[identifier].goodput.append(summary.goodput)
            self.__summaries[identifier].num_requests.append(
                summary.num_requests
            )

    @property
    def workloads(self) -> tp.KeysView[BenchbaseResultsIdentifier]:
        """Get the list of workloads present in the report."""
        return self.__summaries.keys()

    @property
    def summaries(
        self
    ) -> tp.Dict[BenchbaseResultsIdentifier, BenchbaseResultRepsSummary]:
        """Get the summaries of all BenchBase results."""
        return self.__summaries

    def summary(self,
                benchmark: str) -> tp.Optional[BenchbaseResultRepsSummary]:
        for summary in self.__summaries.values():
            if summary.id.benchmark == benchmark:
                return summary
        return None


class MPBenchbaseReport(
    MultiPatchReport,
    shorthand="MP" + BenchBaseReportAggregate.SHORTHAND,
    file_type="zip"
):
    """Multi-patch report for BenchBase benchmark results."""

    def __init__(self, path: Path):
        self.__path = path
        self.__filename = ReportFilename(path)
        self.__patched_reports: tp.Dict[str,
                                        tp.Dict[str,
                                                BenchBaseReportAggregate]] = {}
        self.__base: tp.Dict[str, BenchBaseReportAggregate] = {}

        with tempfile.TemporaryDirectory() as tmp_result_dir:
            shutil.unpack_archive(path, extract_dir=tmp_result_dir)

            for report in Path(tmp_result_dir).iterdir():
                base_name = self._parse_base_file_name_from_report_name(
                    report.stem
                ).removeprefix("mariadbd-")
                if self.is_baseline_report(report.name):
                    # Parse as BenchBaseReportAggregate
                    bbagg_report = BenchBaseReportAggregate(report)
                    if len(bbagg_report.workloads) > 1:
                        raise AssertionError(
                            f"Baseline report {report.name} contains multiple workloads, which is not supported."
                        )

                    self.__base[base_name] = bbagg_report
                elif self.is_patched_report(report.name):
                    if base_name not in self.__patched_reports:
                        self.__patched_reports[base_name] = {}

                    patch_shortname = self._parse_patch_shorthand_from_report_name(
                        report.name
                    )
                    if patch_shortname not in self.__patched_reports[base_name]:
                        self.__patched_reports[base_name][patch_shortname] = []

                    # Parse as BenchBaseReportAggregate
                    bbagg_report = BenchBaseReportAggregate(report)
                    if len(bbagg_report.workloads) > 1:
                        raise AssertionError(
                            f"Patched report {report.name} contains multiple workloads, which is not supported."
                        )

                    self.__patched_reports[base_name][patch_shortname
                                                     ] = bbagg_report

            if not self.__base or not self.__patched_reports:
                raise AssertionError(
                    f"Reports were missing in the file {path=}"
                )

            # Check that all base names are present in both base and patched reports
            for base_name in self.__base:
                if base_name not in self.__patched_reports:
                    raise AssertionError(
                        f"Base report for {base_name} is missing patched reports in the file {path=}"
                    )

    def get_base_names(self) -> tp.List[str]:
        return list(self.__base.keys())

    def get_baseline_for(
        self, base_name: str
    ) -> tp.Optional[BenchBaseReportAggregate]:
        return self.__base.get(base_name, None)

    def get_patched_for(
        self, base_name: str, patch_shortname: str
    ) -> tp.Optional[BenchBaseReportAggregate]:
        if base_name in self.__patched_reports and patch_shortname in self.__patched_reports[
            base_name]:
            return self.__patched_reports[base_name][patch_shortname]
        return None

    @property
    def path(self) -> Path:
        """Path to the report file."""
        return self.__path

    @property
    def filename(self) -> ReportFilename:
        """Filename of the report."""
        return self.__filename

    def get_patch_names(self) -> tp.List[str]:
        """Get the list of patch shortnames present in the report."""
        patch_names = set()
        for patched_reports in self.__patched_reports.values():
            patch_names.update(patched_reports.keys())
        return list(patch_names)
