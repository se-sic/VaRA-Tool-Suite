"""Report class for perf stat output."""

import re
from pathlib import Path

import pandas as pd

from varats.report.report import BaseReport, ReportAggregate


class PerfStatReport(BaseReport, shorthand="PERFSTAT", file_type="json"):
    """Converts perf stat output to a dictionary of data."""

    def __init__(self, path: Path):
        super().__init__(path)
        self.df = pd.read_json(path)
        metrics_of_interest = [
            "%  branch_mispredition_ratio", "%  ic_fetch_miss_ratio",
            "op_cache_fetch_miss_ratio", "of all branches",
            "of all L1-dcache accesses", "all_l2_cache_accesses",
            "all_l2_cache_misses", "all_l2_cache_hits"
        ]
        events_of_interest = ["l3_cache_accesses", "l3_misses"]
        if (
            'interval' in self.df.columns and 'event' in self.df.columns and
            'counter-value' in self.df.columns and
            'metric-unit' in self.df.columns and
            'metric-value' in self.df.columns
        ):
            # Filter events
            event_df = self.df[self.df['event'].isin(events_of_interest)].copy()
            event_df["label"] = event_df["event"]
            event_df["value"] = event_df["counter-value"]

            # Filter metrics
            metric_df = self.df[
                self.df['metric-unit'].isin(metrics_of_interest)].copy()
            metric_df["label"] = metric_df["metric-unit"]
            metric_df["value"] = metric_df["metric-value"]

            combined_df = pd.concat([event_df, metric_df], ignore_index=True)
            combined_df = combined_df.dropna(
                subset=["interval", "label", "value"]
            )

            self.df = combined_df.pivot(
                index="interval", columns="label", values="value"
            ).fillna(0)
            self.df.index.name = "interval"
        else:
            print(
                f"Warning: JSON structure in {path} "
                f"might not be in the expected format."
            )


class PerfStatReportAggregate(
    ReportAggregate[PerfStatReport],
    shorthand=PerfStatReport.SHORTHAND + ReportAggregate.SHORTHAND,
    file_type=ReportAggregate.FILE_TYPE
):
    """Context Manager for parsing multiple Perf Stat reports stored inside a
    zip file."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, PerfStatReport)
