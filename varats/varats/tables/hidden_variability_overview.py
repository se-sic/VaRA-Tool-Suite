import json
import typing as tp
from pathlib import Path

import numpy as np
import pandas as pd
from junitparser import JUnitXml, junitparser

from varats.data.databases.hidden_configurability_database import aggregate_data
from varats.data.reports.hidden_configurability_report import (
    HiddenConfigurabilityReport,
)
from varats.data.reports.text_report import PlainTextReport
from varats.experiments.vara.hidden_configurability_experiments import (
    FindHiddenConfigurationPoints,
    _PROJECT_WORKLOADS,
    PATCH_VARIATIONS,
    TestPatchVariations,
    MPTextReport,
    FilterHiddenConfigurabilityReport,
)
from varats.paper.paper_config import get_loaded_paper_config
from varats.project.project_util import get_local_project_repo
from varats.report.multi_patch_report import MultiPatchReport
from varats.report.report import ReportAggregate
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableGenerator, TableFormat
from varats.ts_utils.cli_util import make_cli_option
from varats.ts_utils.click_param_types import (
    create_single_case_study_choice,
    create_multi_case_study_choice,
)
from varats.utils.git_util import calc_repo_loc
from varats.utils.testsuite_utils import TestStatus


class HiddenVariabilityOverviewTable(Table, table_name="hv_overview"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        table_data = []

        for case_study in case_studies:
            reports = get_processed_revisions_files(
                case_study.project_name,
                FilterHiddenConfigurabilityReport,
                FilterHiddenConfigurabilityReport.report_spec().main_report,
            )

            if not reports:
                continue

            if len(reports) > 1:
                print(f"More than one report for {case_study.project_name}")
                continue

            report = HiddenConfigurabilityReport(reports[0].full_path())

            if report.get_num_configurability_points(
            ) == 0 and self.table_kwargs["hide_zero"]:
                continue

            config_points = report.get_hidden_configurability_points()

            new_row = {
                "Case Study": case_study.project_name,
                "Total (Unfiltered)": report.get_num_configurability_points(),
                "Excluded (Filename)": 0,
                "Excluded (Coverage)": 0,
                "Total (Filtered)": 0
            }

            for kind in config_points:
                filename_excluded = len([
                    point for point in config_points[kind]
                    if "Excluded (Filename)" in point.tags
                ])
                coverage_excluded = len([
                    point for point in config_points[kind]
                    if "Excluded (Coverage)" in point.tags
                ])
                relevant_points = len([
                    point for point in config_points[kind]
                    if "Excluded (Filename)" not in point.tags and
                    "Excluded (Coverage)" not in point.tags
                ])
                new_row["Excluded (Filename)"] += filename_excluded
                new_row["Excluded (Coverage)"] += coverage_excluded
                new_row["Total (Filtered)"] += relevant_points

                new_row[
                    kind
                ] = f"{len(config_points[kind])}/{filename_excluded}/{coverage_excluded}/{relevant_points}"

            table_data.append(new_row)

        df = pd.DataFrame(table_data)

        df.sort_values(by="Case Study", inplace=True)

        return dataframe_to_table(df, table_format, wrap_table=wrap_table)


class HiddenVariabilityOverviewTableGenerator(
    TableGenerator,
    generator_name="hv-overview",
    options=[
        make_cli_option(
            "--hide-zero",
            is_flag=True,
            default=False,
            help="Hide projects with zero hidden configurability points."
        )
    ]
):

    def generate(self) -> tp.List[Table]:
        return [
            HiddenVariabilityOverviewTable(
                self.table_config, **self.table_kwargs
            )
        ]


class HVProjectOverviewTable(Table, table_name="hv_project_overview"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        table_rows = []

        for cs in case_studies:
            if cs.project_name not in _PROJECT_WORKLOADS or cs.project_name not in PATCH_VARIATIONS:
                print(
                    f"Skipping {cs.project_name} as it is not an active HV subject system"
                )
                continue
            cs_workloads = _PROJECT_WORKLOADS[cs.project_name]
            cs_opportunities: dict = PATCH_VARIATIONS[cs.project_name]
            project_repo = get_local_project_repo(cs.project_name)
            locs = calc_repo_loc(project_repo, cs.revisions[0].hash)
            row = {
                "Name":
                    cs.project_name,
                "LOC":
                    locs,
                "|C|":
                    len(cs.get_config_ids_for_revision(cs.revisions[0])),
                "|W|":
                    len(cs_workloads),
                "|O|":
                    len(cs_opportunities),
                "|A|":
                    sum([len(entry[1]) for entry in cs_opportunities.values()]),
            }

            table_rows.append(row)

        df = pd.DataFrame(table_rows).set_index("Name")
        df.sort_index(inplace=True)

        return dataframe_to_table(df, table_format, wrap_table=wrap_table)


class HVProjectOverviewTableGenerator(
    TableGenerator, generator_name="hv_project_overview", options=[]
):

    def generate(self) -> tp.List[Table]:
        return [HVProjectOverviewTable(self.table_config, **self.table_kwargs)]


class HCPerfDetailTable(Table, table_name="hc_perf_detail"):

    @property
    def name(self) -> str:
        return f"{self.NAME}{'_'.join([cs.project_name for cs in self.table_kwargs['case_studies']])}"

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = self.table_kwargs["case_studies"]

        significant_results = pd.DataFrame()

        for case_study in case_studies:
            cs_data = aggregate_data(case_study, None)

            if cs_data.empty:
                continue

            # Filter only significant rows
            def filter_results(row: pd.Series) -> bool:
                # Remove baseline data
                if row["config_opportunity"] == "__baseline__":
                    return False

                if row["metric"] == "wall_clock_time" and np.mean(
                    row["value"]
                ) < 1:
                    return False

                if row["metric"] == "max_resident_size" and np.mean(
                    row["value"]
                ) < 5000:
                    return False

                if row["significance"] >= 0.05:
                    return False

                if abs(row["value_relative"]) < 0.05:
                    return False

                return True

            cs_data = cs_data[cs_data["config_opportunity"] != "__baseline__"]
            cs_data["Project"] = case_study.project_name
            cs_data["value_relative"] = cs_data["value_relative"].apply(
                np.median
            )
            cs_data["significance"] = cs_data["significance"].apply(
                lambda x: x.pvalue
            )
            cs_data = cs_data[cs_data.apply(filter_results, axis=1)]

            cs_data.drop(columns=["value"], inplace=True)
            significant_results = pd.concat([significant_results, cs_data],
                                            ignore_index=True)

        # Rearrange columns
        col_mappings = {
            "config_id": "Config",
            "binary-wl": "Workload",
            "significance": "p-value",
            "config_opportunity": "opportunity",
        }

        column_order = [
            "Project", "metric", "config_id", "binary-wl", "config_opportunity",
            "variation", "significance", "value_relative"
        ]
        significant_results = significant_results[column_order]

        significant_results = significant_results.rename(columns=col_mappings)

        significant_results.sort_values(
            by=["Project", "metric", "Config", "opportunity", "variation"],
            inplace=True
        )

        return dataframe_to_table(
            significant_results, table_format, wrap_table=wrap_table
        )


class HCPerfDetailGenerator(
    TableGenerator,
    generator_name="hc_perf_detail",
    options=[
        make_cli_option(
            "--case-studies",
            type=create_multi_case_study_choice(),
            help="Case studies to include"
        )
    ]
):

    def generate(self) -> tp.List[Table]:
        return [HCPerfDetailTable(self.table_config, **self.table_kwargs)]


def _is_equivalent(base_results, patched_results) -> bool:
    for test_name, base_status in base_results.items():
        if test_name not in patched_results:
            # Not sure how that would happen, but ignore
            continue

        patched_status = patched_results[test_name]

        # We are mostly interested in cases where the base test passed,
        # but the patched test failed in some way
        if base_status == TestStatus.PASSED and patched_status in {
            TestStatus.FAILED, TestStatus.TIMEOUT, TestStatus.UNKNOWN
        }:
            return False

    return True


class PTRAggregate(
    ReportAggregate[PlainTextReport], shorthand="", file_type=""
):

    def __init__(self, path: Path) -> None:
        super().__init__(path, PlainTextReport)


class MPDuneReport(
    MultiPatchReport[ReportAggregate[PlainTextReport]],
    shorthand="",
    file_type=""
):

    def __init__(self, path: Path) -> None:
        super().__init__(path, PTRAggregate)


class ConfigAlternativesValidityTable(
    Table, table_name="hc_alternatives_validity"
):
    __TEST_TO_IGNORE: tp.Dict[str, tp.List[str]] = {
        "libzmq": ["(empty).test_hwm", "(empty).test_hwm_pubsub"],
        "brotli": [],
        "libvpx": [],
        "FastDownward": [],
        "DunePerfRegression": []
    }

    def __parse_gtest_report(self, report: PlainTextReport) -> tp.Any:
        """Parse the gtest report."""
        test_data = json.loads(report.content)

        results = {}

        # Iterate over test suites
        for suite in test_data.get("testsuites", []):
            suite_name = suite.get("name", "<unknown>")

            for case in suite.get("testsuite", []):
                case_name = case.get("name", "<unknown>")
                status = case.get("status", "UNKNOWN").upper()

                if status == "RUN":
                    if "failures" in case:
                        results[f"{suite_name}.{case_name}"] = TestStatus.FAILED
                    else:
                        results[f"{suite_name}.{case_name}"] = TestStatus.PASSED
                elif status == "NOTRUN":
                    results[f"{suite_name}.{case_name}"] = TestStatus.NOT_RUN

        for ignored_test in self.__TEST_TO_IGNORE.get(
            self.table_kwargs["case_study"].project_name, []
        ):
            if ignored_test in results:
                results.pop(ignored_test)

        return results

    def __parse_junit_report(self, report: PlainTextReport) -> tp.Any:
        """Parse the junit report."""
        test_xml = JUnitXml.fromstring(report.content)

        results = {}

        for suite in test_xml:
            suite: junitparser.TestSuite
            suite_name = suite.name if suite.name else "<unknown>"

            for case in suite:
                case: junitparser.TestCase
                case_name = case.name if case.name else "<unknown>"

                if case.is_passed:
                    status = TestStatus.PASSED
                elif case.is_skipped:
                    status = TestStatus.SKIPPED
                elif case.is_failure or case.is_error:
                    status = TestStatus.FAILED
                else:
                    status = TestStatus.UNKNOWN

                results[f"{suite_name}.{case_name}"] = status

        for ignored_test in self.__TEST_TO_IGNORE.get(
            self.table_kwargs["case_study"].project_name, []
        ):
            if ignored_test in results:
                results.pop(ignored_test)

        return results

    def __parse_dune_report(self, agg_report: PTRAggregate) -> tp.Any:
        """Parse the DunePerfRegression report."""
        test_results = {}
        for report in agg_report.reports():
            module_name = report.path.stem.removesuffix("-tests")
            module_results = self.__parse_junit_report(report)
            module_results = {
                f"{module_name}#{k}": v for k, v in module_results.items()
            }
            test_results.update(module_results)

        for ignored_test in self.__TEST_TO_IGNORE.get(
            self.table_kwargs["case_study"].project_name, []
        ):
            if ignored_test in test_results:
                test_results.pop(ignored_test)

        return test_results

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        table_rows = []

        project_testparsers = {
            "brotli": self.__parse_junit_report,
            "libzmq": self.__parse_junit_report,
            "libvpx": self.__parse_gtest_report,
            "FastDownward": self.__parse_junit_report,
            "DunePerfRegression": self.__parse_dune_report,
        }

        cs = self.table_kwargs["case_study"]
        reports = get_processed_revisions_files(
            cs.project_name,
            TestPatchVariations,
            TestPatchVariations.report_spec().main_report,
            only_newest=False
        )

        if len(reports) > 0 and (cs.project_name not in project_testparsers):
            print(f"No test parser for {cs.project_name} defined.")

        for report in reports:
            config_id = report.report_filename.config_id

            if cs.project_name == "DunePerfRegression":
                mp_test_report = MPDuneReport(report.full_path())
            else:
                mp_test_report = MPTextReport(report.full_path())

            base_report = mp_test_report.get_baseline_report()

            baseline_results = project_testparsers[cs.project_name](base_report)

            row = {
                "Config ID": config_id,
                "configuration_opportunity": "__Baseline__",
                "variation": None,
                "same_as_baseline": True
            }

            for status in TestStatus:
                # Count the number of tests that passed, failed, etc.
                row[f"{status.value}"] = sum(
                    1 for test in baseline_results.values() if test == status
                )
            table_rows.append(row)

            # We want to identify all patched reports in which the
            # test result differs from the baseline
            for patch_name in mp_test_report.get_patch_names():
                patched_report = mp_test_report.get_report_for_patch(patch_name)
                if not patched_report:
                    print(f"No patched report for {patch_name}?")
                    continue
                patched_results = project_testparsers[cs.project_name
                                                     ](patched_report)

                base_name, value = patch_name.split("=", 1)
                row = {
                    "Config ID":
                        config_id,
                    "configuration_opportunity":
                        base_name,
                    "variation":
                        value,
                    "same_as_baseline":
                        _is_equivalent(baseline_results, patched_results)
                }

                for status in TestStatus:
                    # Count the number of tests that passed, failed, etc.
                    row[f"{status.value}"] = sum(
                        1 for test in patched_results.values() if test == status
                    )

                table_rows.append(row)

        df = pd.DataFrame(table_rows)
        df.sort_values(
            by=["Config ID", "configuration_opportunity", "variation"],
            inplace=True
        )

        summary_rows = []
        for configuration_opportunity in df["configuration_opportunity"].unique(
        ):
            if configuration_opportunity == "__Baseline__":
                continue

            row = {
                "configuration_opportunity": configuration_opportunity,
            }

            opportunity_df = df[df["configuration_opportunity"] ==
                                configuration_opportunity]
            total_alternatives = len(opportunity_df["variation"].unique())

            for config_id in opportunity_df["Config ID"].unique():
                config_df = opportunity_df[opportunity_df["Config ID"] ==
                                           config_id]
                num_equivalent = len(
                    config_df[config_df["same_as_baseline"] == True
                             ]  # noqa: E712
                )
                row[int(config_id)] = f"{num_equivalent}/{total_alternatives}"

            summary_rows.append(row)

        summary_df = pd.DataFrame(summary_rows
                                 ).set_index("configuration_opportunity")

        return dataframe_to_table(
            summary_df, table_format, wrap_table=wrap_table
        )


class ConfigAlternativesGenerator(
    TableGenerator,
    generator_name="hc_alternatives_validity",
    options=[
        make_cli_option(
            "--case_study",
            type=create_single_case_study_choice(),
            required=True,
            help="Case studies to plot",
        )
    ]
):

    def generate(self) -> tp.List[Table]:
        return [
            ConfigAlternativesValidityTable(
                self.table_config, **self.table_kwargs
            )
        ]


_ACTIVE_HV_PROJECTS = [
    "Ect", "lrzip", "7zip", "brotli", "bzip2", "xz", "lepton", "libzmq"
]


class HCPerfSummaryTable(Table, table_name="hc_perf_summary"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        table_rows = []

        for cs in case_studies:
            if cs.project_name not in _ACTIVE_HV_PROJECTS or cs.project_name not in PATCH_VARIATIONS:
                print(
                    f"Skipping {cs.project_name} as it is not an active HV subject system"
                )
                continue
            cs_data = aggregate_data(cs, None)

            # For each row, we want to summarize the performance impact
            # of all configuration opportunities

            # Columns: Project Name, |A| (Number of alternatives), Metric, |S| (Number of significant performance impacts), |S+| (Number of significant positive impacts), |S-| (Number of significant negative impacts), Impact Range (min, max)

            # For simplicity, we only consider one workload per project here
            workload = _PROJECT_WORKLOADS[cs.project_name][0]

            if cs_data.empty:
                continue

            if cs.project_name == "libzmq":
                # Special case for libzmq as the workload names are a bit inconsistent
                workload = "bench-inproc"

            # Filter CS datat based on bianry-wl column
            # No exact string match possible so we test if workload is a substring
            cs_data = cs_data[
                cs_data["binary-wl"].apply(lambda x: workload in x)]

            # Filter out baseline rows
            cs_data = cs_data[cs_data["config_opportunity"] != "__baseline__"]

            metrics = cs_data["metric"].unique()

            for metric in metrics:
                metric_data = cs_data[cs_data["metric"] == metric]

                new_row = {
                    "Name": cs.project_name,
                    "|A|": 0,
                    "Metric": metric,
                    "|S|": 0,
                    "|S+|": 0,
                    "|S-|": 0,
                    "Impact Range": (None, None),
                }

                for config_opportunity in metric_data["config_opportunity"
                                                     ].unique():
                    opportunity_data = metric_data[
                        metric_data["config_opportunity"] == config_opportunity]

                    # Filter all rows where the significance pvalue is < 0.05
                    # Each row has a object where the pvalue is stored in a field named pvalue
                    significant_impacts = opportunity_data[opportunity_data[
                        "significance"].apply(lambda x: x.pvalue < 0.05)]

                    new_row["|A|"] += len(
                        opportunity_data["variation"].unique()
                    )
                    new_row["|S|"] += len(significant_impacts)
                    if not significant_impacts.empty:
                        means = significant_impacts["value_relative"].apply(
                            np.mean
                        )
                        new_row["|S+|"] += int((means > 0).sum())
                        new_row["|S-|"] += int((means < 0).sum())

                        new_row["Impact Range"] = (
                            min(new_row["Impact Range"][0], means.min())
                            if new_row["Impact Range"][0] is not None else
                            means.min(),
                            max(new_row["Impact Range"][1], means.max())
                            if new_row["Impact Range"][1] is not None else
                            means.max()
                        )

                # Convert Impact Range to normal floats
                new_row["Impact Range"] = (
                    float(new_row["Impact Range"][0])
                    if new_row["Impact Range"][0] is not None else "N/A",
                    float(new_row["Impact Range"][1])
                    if new_row["Impact Range"][1] is not None else "N/A"
                )

                table_rows.append(new_row)

        df = pd.DataFrame(table_rows).set_index("Name")
        df.sort_index(inplace=True)

        return dataframe_to_table(df, table_format, wrap_table=wrap_table)


class HCPerfSummaryGenerator(
    TableGenerator, generator_name="hc_perf_summary", options=[]
):

    def generate(self) -> tp.List[Table]:
        return [HCPerfSummaryTable(self.table_config, **self.table_kwargs)]
