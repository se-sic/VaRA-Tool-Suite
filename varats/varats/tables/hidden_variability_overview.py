import json
import typing as tp
from pathlib import Path

import numpy as np
import pandas as pd
from junitparser import JUnitXml, junitparser

from varats.data.cache_helper import cache_dataframe, load_cached_df_or_none
from varats.data.databases.hidden_configurability_database import (
    aggregate_data,
)
from varats.data.reports.hidden_configurability_report import (
    HiddenConfigurabilityReport,
)
from varats.data.reports.text_report import PlainTextReport
from varats.experiments.vara.hidden_configurability_experiments import (
    _PROJECT_WORKLOADS,
    FilterHiddenConfigurabilityReport,
    MPTextReport,
    TestPatchVariations,
)
from varats.paper.paper_config import get_loaded_paper_config
from varats.project.project_util import get_local_project_repo
from varats.report.multi_patch_report import MultiPatchReport
from varats.report.report import ReportAggregate
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.cli_util import make_cli_option
from varats.ts_utils.click_param_types import (
    create_multi_case_study_choice,
    create_single_case_study_choice,
)
from varats.utils.git_util import calc_repo_loc
from varats.utils.testsuite_utils import TestResult


class HiddenVariabilityOverviewTable(Table, table_name="hv_overview"):

    __AUTOMATED_EXCLUSION_REASONS = ["Filename", "Coverage", "Operand"]

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
                "Total (Unfiltered)": 0,
                "Filtered (Automated)": 0,
                "Filtered (Manual)": 0,
                "Configuration Opportunities": 0
            }

            for kind in config_points:
                points = config_points[kind]

                new_row["Total (Unfiltered)"] += len(points)

                excl_auto = 0
                excl_manual = 0
                conf_opps = 0

                for point in points:
                    if "conf_opp" in point.tags:
                        conf_opps += 1

                    if any(
                        f"Excluded ({reason})" in point.tags
                        for reason in self.__AUTOMATED_EXCLUSION_REASONS
                    ):
                        excl_auto += 1
                    # Manually filtered points have tags like "Excluded (<reason>)"
                    elif any(
                        tag.startswith("Excluded (") and tag.endswith(")")
                        for tag in point.tags
                    ):
                        excl_manual += 1

                new_row["Filtered (Automated)"] += excl_auto
                new_row["Filtered (Manual)"] += excl_manual
                new_row["Configuration Opportunities"] += conf_opps

                if self.table_kwargs["per_category"]:
                    new_row[
                        kind
                    ] = f"{len(points)}/{excl_auto}/{excl_manual}/{conf_opps}"

            table_data.append(new_row)

        # Add dummy data for missing case studies to ensure consistent table structure
        _missing_cs = [
            "duckdb",
            "mysql",
            "noisepage",
            "vireo",
            "z3",
            "CryptoMiniSat",
            "CP-SAT",
            "Cadical",
            "MapleSAT",
            "fmt",
        ]

        for cs in _missing_cs:
            # Add a dummy row for case studies with currently missing data
            table_data.append({
                "Case Study": cs,
                "Total (Unfiltered)": "N/A",
                "Filtered (Automated)": "N/A",
                "Filtered (Manual)": "N/A",
                "Configuration Opportunities": "N/A"
            })

        df = pd.DataFrame(table_data)

        # Sort by case study name, but put the missing ones at the end
        df["Case Study"] = pd.Categorical(
            df["Case Study"],
            categories=[
                cs["Case Study"]
                for cs in table_data
                if cs["Total (Unfiltered)"] != "N/A"
            ] + [
                cs["Case Study"]
                for cs in table_data
                if cs["Total (Unfiltered)"] == "N/A"
            ],
            ordered=True
        )
        df.sort_values("Case Study", inplace=True)

        # Set case study name as index
        df.set_index("Case Study", inplace=True)

        return dataframe_to_table(df, table_format, wrap_table=wrap_table)


class HiddenVariabilityOverviewTableGenerator(
    TableGenerator,
    generator_name="hv_overview",
    options=[
        make_cli_option(
            "--hide-zero",
            is_flag=True,
            default=False,
            help="Hide projects with zero hidden configurability points."
        ),
        make_cli_option(
            "--per-category",
            is_flag=True,
            default=False,
            help="Show breakdown of hidden configurability points by category."
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
    __CACHE_ID = "hv_project_overview_table"

    def _cache_overview_df(self, project_name: str, df: pd.DataFrame) -> None:
        cache_dataframe(self.__CACHE_ID, project_name, df)

    def _load_cached_overview_df(self, project_name: str) -> pd.DataFrame:
        dtypes = {
            "Project": str,
            "Domain": str,
            "LOC": int,
            "|CL|": int,
            "|CO|": int,
            "|S|": int,
        }

        return load_cached_df_or_none(self.__CACHE_ID, project_name, dtypes)

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        result_df = pd.DataFrame()

        for cs in case_studies:
            cs_df = self._load_cached_overview_df(cs.project_name)

            if cs_df is None:
                print(f"Processing {cs.project_name}...")
                reports = get_processed_revisions_files(
                    cs.project_name,
                    FilterHiddenConfigurabilityReport,
                    FilterHiddenConfigurabilityReport.report_spec().main_report,
                )

                if not reports:
                    print(f"No report for {cs.project_name}")
                    continue

                if len(reports) > 1:
                    print(f"More than one report for {cs.project_name}")
                    continue

                report = HiddenConfigurabilityReport(reports[0].full_path())

                project_repo = get_local_project_repo(cs.project_name)
                locs = calc_repo_loc(project_repo, cs.revisions[0].hash)

                num_configs = len(cs.get_config_ids_for_revision(cs.revisions[0]))
                if num_configs == 0:
                    # Just the default configuration
                    num_configs = 1

                num_workloads = len(_PROJECT_WORKLOADS[cs.project_name])

                num_metrics = 2 # Currently two for all our projects.
                # Proper solution would be to load the performance data and count the unique metrics
                # but that is a bit too much overhead for now.


                row = {
                    "Project":
                        cs.project_name,
                    "Domain":
                        cs.project_cls.DOMAIN,
                    "LOC":
                        locs,
                    "|L|":
                        report.get_num_configurability_points(),
                    "|O|":
                        sum([
                            len(p) for _, p in
                            report.get_points_with_tag("conf_opp").items()
                        ]),
                    "|S|": num_metrics * num_workloads * num_configs
                }
                cs_df = pd.DataFrame([row])
                self._cache_overview_df(cs.project_name, cs_df)
            result_df = pd.concat([result_df, cs_df], ignore_index=True)

        df = result_df.reset_index(drop=True)
        # Sort by domain first, then by project name
        df.sort_values(by=["Domain", "Project"], inplace=True)

        kwargs = {}
        style = df.style.hide(axis="index")
        if table_format == TableFormat.LATEX:
            # Format LOC with thousands separator
            df["LOC"] = df["LOC"].apply(lambda x: f"{x:,}")

            # Wrap project names in \textsc{}
            df["Project"] = df["Project"].apply(lambda x: f"\\textsc{{{x}}}")

            kwargs["hrules"] = True
            kwargs[
                "caption"
            ] = ("Overview of our subject systems grouped by domain. "
                 "For each subject system, we show the total lines of code (LOC), the number of \\canlocs{} (|CL|), and the number of \\conopps{} (|CO|).")
            kwargs["label"] = "tab:subject_systems"

        return dataframe_to_table(
            df, table_format, wrap_table=wrap_table, style=style, **kwargs
        )


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
        if base_status == TestResult.PASSED and patched_status in {
            TestResult.FAILED, TestResult.TIMEOUT, TestResult.UNKNOWN
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
                        results[f"{suite_name}.{case_name}"] = TestResult.FAILED
                    else:
                        results[f"{suite_name}.{case_name}"] = TestResult.PASSED
                elif status == "NOTRUN":
                    results[f"{suite_name}.{case_name}"] = TestResult.NOT_RUN

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
                    status = TestResult.PASSED
                elif case.is_skipped:
                    status = TestResult.SKIPPED
                elif case.is_failure or case.is_error:
                    status = TestResult.FAILED
                else:
                    status = TestResult.UNKNOWN

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

            for status in TestResult:
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

                for status in TestResult:
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


