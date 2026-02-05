import json
import typing as tp
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import xmltodict

from varats.report.report import BaseReport, ReportAggregate


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


class BenchBaseReportAggregate(
    ReportAggregate[BenchBaseReport],
    shorthand=BenchBaseReport.SHORTHAND + ReportAggregate.SHORTHAND,
    file_type=ReportAggregate.FILE_TYPE
):
    """Aggregate multiple BenchBase reports into a single report."""

    def __init__(self, path: Path):
        super().__init__(path, BenchBaseReport)

        # TODO: Ensure that all reports have the same set of workloads
