import ast
import typing as tp
from collections import defaultdict
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, ttest_ind, kruskal

from varats.data.cache_helper import cache_dataframe, load_cached_df_or_none
from varats.data.reports.hidden_configurability_report import MPRTimeWLAggregate
from varats.experiments.base.run_workloads import RunPatchedWorkloads
from varats.experiments.hidden_config.benchbase_experiments import (
    BenchbaseHiddenConfig,
    MPBenchbaseReport,
)
from varats.experiments.hidden_config.hidden_config_utils import (
    get_all_variations_as_dict,
)
from varats.experiments.vara.hidden_configurability_experiments import (
    MPTextReport,
    TestPatchVariations,
    TimePatchedWorkloads,
    variation_value_to_str,
)
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.projects.cpp_projects.libzmq import LibZMQMPReport, LibZMQWLAggregate
from varats.report.gnu_time_report import WLTimeReportAggregate
from varats.revision.revisions import get_processed_revisions_files

CACHE_DATA_ID = "hc_database"

ACTIVE_HV_PROJECTS = [
    "lrzip",
    "7zip",
    "brotli",
    "bzip2",
    "xz",
    "libzmq",
    "FastDownward",
    #"libvpx",
    "mariadb",
    "postgresql",
    "cryptominisat",
    "cadical"
]


def extract_config_point(full_name: str) -> tp.Tuple[str, str]:
    # patch names follow the pattern "patched_<len>_<config_point>=<value>_<base-name>.zip"
    # Where <len> is the length of the <config_point>=<value>
    # We want to extract <config_point> and <value>
    # Example: "patched_15_opt_level=3_basefile.c.zip" -> ("opt_level", "3")
    name_path = Path(full_name).stem
    name_path = name_path[len("patched_"):]
    split_leftover_fn = name_path.partition("_")
    shortname_length = int(split_leftover_fn[0])
    config_part = "".join(split_leftover_fn[2:])[:shortname_length]
    config_point = config_part.split('=')
    return config_point[0], config_point[1]


def get_configuration_points(report_file: MPRTimeWLAggregate) -> tp.List[str]:
    result = set()

    for patch_name in report_file.get_patch_names():
        # patch names follow the pattern "<patch_name>_<base_file_name>_<config_point>=<value>"
        # We are interested in the unique configuration points
        result.add(extract_config_point(patch_name)[0])

    return list(result)

def filter_for_significant_changes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter rows to relevant ones for evaluation.

    The rows are relevant iff:
    - The change is statistically significant (p-value < 0.05)
    - The change has at least a small effect size (Cohen's d >= 0.2)
    """
    return df[(df["significance"].
               apply(lambda x: x.pvalue < 0.05)
           ) & (df["effect_size"].
               apply(lambda x: abs(x)
                     >= EffectSize.SMALL)
           )]

def filter_baseline_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Filter rows to only include baseline rows."""
    return df[df["config_opportunity"] != "__baseline__"]

def get_data_for_single_config(
    cs: CaseStudy, config_id: int | None = None
) -> pd.DataFrame:
    """Get data for a single configuration ID."""
    result_df = _load_cached_df(cs.project_name, config_id)

    if result_df is None:
        # Case distinction for specific projects
        if cs.project_name == "libzmq":
            # TODO: Update for use with multiple binaries
            df1 = _get_data_single_config_default(cs, config_id)
            # binary-wl names are "{bin}/{wl}" from this report,
            # but just "{wl}" from the libzmq-specific report,
            # so we need to adjust the binary-wl names in this
            df1["binary-wl"] = df1["binary-wl"].apply(lambda x: x.split("/")[-1])

            df2 = _get_data_single_config_libzmq(cs, config_id)
            result_df = pd.concat([df1, df2], ignore_index=True)

        elif cs.project_name in ["mariadb", "postgresql", "mysql"]:
            result_df = _get_data_single_config_benchbase(cs, config_id)
        else:
            result_df = _get_data_single_config_default(cs, config_id)

        # Enrich data with testsuite information
        if not result_df.empty:
            _cache_df(result_df, cs.project_name, config_id)

    return result_df

def calculate_kruskal_wallis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Kruskal-Wallis H-test based on the value_relative column.

    Calculates for two dimensions:
        1. Fixing a setting (Combination of binary-wl, metric, and config_id)
          --> are there differences between the variations of this setting?
        2. Fixing a configuration alternative (Combination of config_opportunity and variation)
         --> are there differences between the different binary-wl, config_id
            and metric combinations for this configuration alternative?
    Receives as input the full dataframe including data for all projects.
    Returns a summary dataframe with the columns:
        - project: Project name
        - num_settings: Number of settings with at least two variations that are significantly different from the baseline
        - num_sig
    """
    result_df = df.copy()

    # Filter out baseline rows
    filtered_df = filter_baseline_rows(result_df)

    # Select only significant changes
    significant_df = filter_for_significant_changes(filtered_df)

    # Group by binary-wl, metric, and config_id, then calculate the Kruskal-Wallis H-test
    def kruskal_wallis(group):
        if len(group) < 2:
            return pd.Series({"kruskal_statistic": np.nan, "kruskal_pvalue": np.nan})

        # Extract the value_relative lists for each variation
        data = [row["value_relative"] for _, row in group.iterrows()]

        # Perform the Kruskal-Wallis H-test
        statistic, pvalue = kruskal(*data)

        return pd.Series({"kruskal_statistic": statistic, "kruskal_pvalue": pvalue})

    projects = df["project"].unique()

    data_rows = []

    for p in projects:
        print(f"Calculating Kruskal-Wallis H-test for project {p}...")
        project_df = significant_df[significant_df["project"] == p].fillna(-1)

        if project_df.empty:
            print(f"No significant changes found for project {p}, skipping Kruskal-Wallis H-test.")
            continue

        setting_summary = project_df.groupby(
            ["binary-wl", "metric", "config_id"])

        num_settings = setting_summary.ngroups

        # For each setting, collect the value_relative lists for all variations and perform the Kruskal-Wallis H-test
        setting_results = setting_summary.apply(kruskal_wallis)
        num_sig_settings = setting_results[setting_results["kruskal_pvalue"] < 0.05].shape[0]

        # Repeat for configuration alternatives
        config_alt_summary = project_df.groupby(["config_opportunity", "variation"])
        num_conf_alts = config_alt_summary.ngroups
        config_alt_results = config_alt_summary.apply(kruskal_wallis)
        num_sig_config_alts = config_alt_results[config_alt_results["kruskal_pvalue"] < 0.05].shape[0]

        data_rows.append({
            "project": p,
            "num_settings": num_settings,
            "num_sig_settings": num_sig_settings,
            "num_config_alts": num_conf_alts,
            "num_sig_config_alts": num_sig_config_alts
        })

    return pd.DataFrame.from_records(data_rows)

def _add_testsuite_info(
    df: pd.DataFrame,
    cs: CaseStudy,
    config_id: tp.Optional[int] = None
) -> pd.DataFrame:
    result_files = get_processed_revisions_files(
        cs.project_name,
        TestPatchVariations,
        TestPatchVariations.report_spec().main_report,
        get_case_study_file_name_filter(cs),
        config_id=config_id,
        only_newest=False,
    )

    if len(result_files) != 1:
        print(
            f"Expected exactly one result file for TestPatchVariations, but found {len(result_files)} for {cs.project_name} ({config_id=})"
        )
        return df

    report: TestPatchVariations = MPTextReport(result_files[0].full_path())
    ...
    #TODO: Implement this function to add testsuite information to the DataFrame based on the report

    return df


def _get_data_single_config_libzmq(
    cs, config_id: tp.Optional[int] = None
) -> pd.DataFrame:
    # Load all result files from RunAllWorkloads experiment
    result_files = get_processed_revisions_files(
        "libzmq",
        RunPatchedWorkloads,
        RunPatchedWorkloads.report_spec().main_report,
        get_case_study_file_name_filter(cs),
        config_id=config_id,
        only_newest=False,
    )

    if len(result_files) == 0:
        print(f"No results found for {cs.project_name} ({config_id=})")
        return pd.DataFrame()

    data_rows = []
    base_values = {}

    def _extract_baselines_from_report(report: LibZMQWLAggregate,
                                       metric: str,
                                       config_id: tp.Optional[int],
                                       base_values):
        result = [{
                    "binary-wl": f"{wl}",
                    "config_opportunity": "__baseline__",
                    "variation": None,
                    "metric": metric,
                    "value": report.metrics[metric][wl],
                    "config_id": config_id,
                } for wl in report.workload_names()]

        base_values[metric] = { wl: np.mean(report.metrics[metric][wl])
                                for wl in report.workload_names() }

        return result

    def _extract_patched_values_from_report(report: LibZMQWLAggregate,
                                            metric: str,
                                            config_id: tp.Optional[int],
                                            config_opportunity: str,
                                            variation: str,
                                            base_values,
                                            negate_relative: bool = False):
        metric_values = {
            wl: report.metrics[metric][wl]
            for wl in report.workload_names()
        }

        return [{
                    "binary-wl": f"{wl}",
                    "config_opportunity": config_opportunity,
                    "variation": variation,
                    "metric": metric,
                    "value": metric_values[wl],
                    "value_relative": [float((t / base_values[metric][wl]) - 1)
                                       * (-1 if negate_relative else 1)
                                       for t in metric_values[wl]],
                    "config_id": config_id,
                } for wl in report.workload_names()]



    for result_file in result_files:
        # Load report as LibZMQMPReport
        report: LibZMQMPReport = LibZMQMPReport(result_file.full_path())

        for binary in report.binaries:
            base_report = report.baseline(binary)
            if "inproc_lat" in base_report.filename.filename:
                metric = "latency"
                new_rows = _extract_baselines_from_report(base_report,
                                                          metric,
                                                          config_id,
                                                          base_values)
                data_rows.extend(new_rows)

            elif "inproc_thr" in base_report.filename.filename:
                new_rows = _extract_baselines_from_report(base_report,
                                                            "throughput_mb",
                                                            config_id,
                                                            base_values)
                data_rows.extend(new_rows)

            elif "benchmark_radix_tree" in base_report.filename.filename:
                new_rows = _extract_baselines_from_report(base_report,
                                                            "trie_lookup_time",
                                                            config_id,
                                                            base_values)
                data_rows.extend(new_rows)

                new_rows = _extract_baselines_from_report(base_report,
                                                            "radix_tree_time",
                                                            config_id,
                                                            base_values)
                data_rows.extend(new_rows)

            for patch_name in report.get_patch_names():
                patched_report = report.patched(binary, patch_name)
                opportunity, variation = extract_config_point(patched_report.filename.filename)

                if "inproc_lat" in patched_report.filename.filename:
                    data_rows.extend(_extract_patched_values_from_report(
                        patched_report,
                            metric,
                            config_id,
                            opportunity,
                            variation,
                            base_values,
                            negate_relative=True
                    ))
                elif "inproc_thr" in patched_report.filename.filename:
                    data_rows.extend(
                        _extract_patched_values_from_report(
                            patched_report,
                            "throughput_mb",
                            config_id,
                            opportunity,
                            variation,
                            base_values
                        )
                    )
                elif "benchmark_radix_tree" in patched_report.filename.filename:
                    data_rows.extend(
                        _extract_patched_values_from_report(
                            patched_report,
                            "trie_lookup_time",
                            config_id,
                            opportunity,
                            variation,
                            base_values,
                            negate_relative=True
                        )
                    )

                    data_rows.extend(
                        _extract_patched_values_from_report(
                            patched_report,
                            "radix_tree_time",
                            config_id,
                            opportunity,
                            variation,
                            base_values,
                            negate_relative=True
                        )
                    )

    return pd.DataFrame.from_records(data_rows)



def _get_data_single_config_default(
    cs: CaseStudy, config_id: tp.Optional[int] = None
) -> pd.DataFrame:
    result_files = get_processed_revisions_files(
        cs.project_name,
        TimePatchedWorkloads,
        TimePatchedWorkloads.report_spec().main_report,
        get_case_study_file_name_filter(cs),
        config_id=config_id,
        only_newest=False,
    )

    if len(result_files) == 0:
        print(f"No results found for {cs.project_name} ({config_id=})")
        return pd.DataFrame()

    data_rows = []

    for result_file in result_files:
        report: MPRTimeWLAggregate = MPRTimeWLAggregate(result_file.full_path())

        for binary in report.binaries:
            base_times = {}
            base_rss = {}
            base_report: WLTimeReportAggregate = report.baseline(binary)

            for wl in base_report.workload_names():
                data_rows.extend([{
                    "binary-wl": f"{binary}/{wl}",
                    "config_opportunity": "__baseline__",
                    "variation": None,
                    "metric": "wall_clock_time",
                    "value": base_report.measurements_wall_clock_time(wl),
                    "value_relative": None,
                    "config_id": report.filename.config_id,
                }, {
                    "binary-wl": f"{binary}/{wl}",
                    "config_opportunity": "__baseline__",
                    "variation": None,
                    "metric": "max_resident_size",
                    "value": base_report.max_resident_sizes(wl),
                    "value_relative": None,
                    "config_id": report.filename.config_id,
                }])

                base_times[wl] = np.mean(
                    base_report.measurements_wall_clock_time(wl)
                )
                base_rss[wl] = np.mean(base_report.max_resident_sizes(wl))

            for patch_name in report.get_patch_names():
                patch_report = report.patched(binary, patch_name)
                cp = extract_config_point(patch_report.filename.filename)

                for wl in patch_report.workload_names():
                    data_rows.extend([{
                        "binary-wl": f"{binary}/{wl}",
                        "config_opportunity": f"{cp[0]}",
                        "variation": cp[1].strip("_"),
                        "metric": "wall_clock_time",
                        "value": patch_report.measurements_wall_clock_time(wl),
                        "value_relative": [
                            float((t / base_times[wl]) - 1) * -1
                            for t in patch_report.measurements_wall_clock_time(wl)
                        ],
                        "config_id": report.filename.config_id,
                    }, {
                        "binary-wl": f"{binary}/{wl}",
                        "config_opportunity": f"{cp[0]}",
                        "variation": cp[1].strip("_"),
                        "metric": "max_resident_size",
                        "value": patch_report.max_resident_sizes(wl),
                        "value_relative": [
                            float((t / base_rss[wl]) - 1) * -1
                            for t in patch_report.max_resident_sizes(wl)
                        ],
                        "config_id": report.filename.config_id,
                    }])


    return pd.DataFrame.from_records(data_rows)



def _get_data_single_config_benchbase(
    cs: CaseStudy, config_id: tp.Optional[int] = None
) -> pd.DataFrame:
    result_files = get_processed_revisions_files(
        cs.project_name,
        BenchbaseHiddenConfig,
        BenchbaseHiddenConfig.report_spec().main_report,
        get_case_study_file_name_filter(cs),
        config_id=config_id,
        only_newest=False,
    )

    if len(result_files) == 0:
        print(f"No results found for {cs.project_name} ({config_id=})")
        return pd.DataFrame()

    data_rows = []
    base_data = {
        "throughput": {},
        "latency_avg": {},
    }

    for result_file in result_files:
        report: MPBenchbaseReport = MPBenchbaseReport(result_file.full_path())
        binary = report.filename.binary_name

        patch_names = report.get_patch_names()

        for base_name in report.get_base_names():
            baseline_report = report.get_baseline_for(base_name)

            if baseline_report is None:
                continue

            base_latencies = [l.average_latency for l in
                              baseline_report.summary(base_name).latencies]

            data_rows.extend([
                {
                    "binary-wl": f"{binary}/{base_name}",
                    "config_opportunity": "__baseline__",
                    "variation": None,
                    "metric": "throughput",
                    "value": baseline_report.summary(base_name).throughput,
                    "value_relative": None,
                    "config_id": report.filename.config_id,
                },
                {
                    "binary-wl": f"{binary}/{base_name}",
                    "config_opportunity": "__baseline__",
                    "variation": None,
                    "metric": "latency_avg",
                    "value": base_latencies,
                    "value_relative": None,
                    "config_id": report.filename.config_id,
                }
            ])

            base_data["throughput"][base_name] = np.mean(
                baseline_report.summary(base_name).throughput
            )
            base_data["latency_avg"][base_name] = np.mean(
                base_latencies
            )

            for patch_name in patch_names:
                patched_report = report.get_patched_for(base_name, patch_name)

                if patched_report is None:
                    continue

                cp = patch_name.split("=")[0], patch_name.split("=")[-1]

                latencies = [l.average_latency for l in patched_report.summary(base_name).latencies]

                data_rows.extend([{
                    "binary-wl": f"{binary}/{base_name}",
                    "config_opportunity": f"{cp[0]}",
                    "variation": cp[1],
                    "metric": "throughput",
                    "value": patched_report.summary(base_name).throughput,
                    "value_relative": [
                        float((t / base_data["throughput"][base_name]) - 1)
                        for t in patched_report.summary(base_name).throughput
                    ],
                    "config_id": report.filename.config_id,
                }, {
                    "binary-wl": f"{binary}/{base_name}",
                    "config_opportunity": f"{cp[0]}",
                    "variation": cp[1],
                    "metric": "latency_avg",
                    "value": latencies,
                    "value_relative": [
                        # For latency, lower is better
                        float((t / base_data["latency_avg"][base_name]) - 1) * -1
                        for t in latencies
                    ],
                    "config_id": report.filename.config_id,
                }])

    return pd.DataFrame.from_records(data_rows)


def _load_cached_df(
    project_name: str,
    config_id: tp.Optional[int] = None
) -> tp.Optional[pd.DataFrame]:
    dtypes = {
        "binary-wl": "str",
        "config_opportunity": "str",
        "variation": "str",
        "metric": "str",
        "value": "str",
        "value_relative": "str",
        "config_id": "Int64",
    }
    df = load_cached_df_or_none(
        f"{CACHE_DATA_ID}-{config_id}", project_name, dtypes
    )

    if df is None:
        return None

    # Convert columns "value" and "value_relative" back to lists
    df["value"] = df["value"].apply(ast.literal_eval)
    df["value_relative"] = df["value_relative"].apply(
        lambda x: ast.literal_eval(x) if pd.notna(x) else None
    )

    return df


def _cache_df(
    df: pd.DataFrame,
    project_name: str,
    config_id: tp.Optional[int] = None
) -> None:
    df_copy = df.copy()
    # Convert columns "value" and "value_relative" to string to store lists in csv
    df_copy["value"] = df_copy["value"].apply(str)
    df_copy["value_relative"] = df_copy["value_relative"].apply(str)

    cache_dataframe(f"{CACHE_DATA_ID}-{config_id}", project_name, df_copy)


def aggregate_data(
    cs: CaseStudy, config_ids: tp.Optional[tp.List[int]]
) -> pd.DataFrame:
    result_df = pd.DataFrame()

    if config_ids is None:
        config_ids = cs.get_config_ids_for_revision(cs.revisions[0])

    if len(config_ids) == 0:
        config_ids = [None]

    for config_id in config_ids:
        config_df = get_data_for_single_config(cs, config_id)

        result_df = pd.concat([result_df, config_df], ignore_index=True)

    result_df = add_significance_values(result_df)

    return result_df


def create_config_opportunities_value_map(
    cs: CaseStudy
) -> tp.Dict[str, tp.Dict[str, float]]:
    """Create a mapping of configuration opportunities to their values."""
    result = {}

    patches = get_all_variations_as_dict(cs)

    for patch_name, config_opportunity in patches.items():
        arg_name, values = config_opportunity
        if cs.project_name == "DunePerfRegression":
            result[f"{patch_name}_{arg_name}"] = {
                variation_value_to_str(value): value for value in values
            }
        elif cs.project_name in ["FastDownward", "mariadb"]:
            result[f"{patch_name}"] = {
                variation_value_to_str(value): value for value in values
            }
        else:
            result[arg_name] = {
                variation_value_to_str(value): value for value in values
            }

    if cs.project_name == "FastDownward":
        # Special case for FastDownward where we have multiple config opportunities
        result["preconditions"] = result["preconditions_to_test"]

    if cs.project_name == "libvpx":
        result["min_filter_pick"] = result["min_filter_level"]
        result["min_filter_search"] = result["min_filter_level"]
        result["pred_stride_rd"] = result["pred_stride"]
        result["vp9_enc_block_size"] = result["block_size"]
        result["one_pass_cq_adjust"] = result["cq_adjust"]
        result["two_pass_cq_adjust"] = result["cq_adjust"]

    return result


def add_significance_values(df: pd.DataFrame) -> pd.DataFrame:
    """Add significance values to the DataFrame."""
    if df.empty:
        return df
    # First identify all baseline rows
    baseline_df = df[df["config_opportunity"] == "__baseline__"].set_index([
        "binary-wl", "metric", "config_id"
    ])["value"]

    def is_significant(row):
        if (row["config_opportunity"] == "__baseline__"):
            return None
        baseline_value = baseline_df.loc[row["binary-wl"], row["metric"],
                                         row["config_id"]].copy()
        return mannwhitneyu(baseline_value, row["value"])

    df["significance"] = df.apply(is_significant, axis=1)

    def cohens_d(row):
        if (row["config_opportunity"] == "__baseline__"):
            return None
        baseline_value = baseline_df.loc[row["binary-wl"], row["metric"],
                                         row["config_id"]]

        def s(x1, x2):
            return np.sqrt(((len(x1) - 1) * np.std(x1, ddof=1)**2 +
                            (len(x2) - 1) * np.std(x2, ddof=1)**2) /
                           (len(x1) + len(x2) - 2))

        return (np.mean(row["value"]) -
                np.mean(baseline_value)) / s(row["value"], baseline_value)

    df["cohens_d"] = df.apply(cohens_d, axis=1)

    def r(row):
        if (row["config_opportunity"] == "__baseline__"):
            return None
        return row["significance"].statistic / np.sqrt(
            len(row["value"]) + len(
                baseline_df.loc[row["binary-wl"], row["metric"],
                                row["config_id"]]
            )
        )

    df["r"] = df.apply(r, axis=1)

    df["effect_size"] = df["r"].apply(
        lambda x: EffectSize.interpret(x) if pd.notna(x) else EffectSize.NONE
    )

    return df


def get_regressing_configs(
    cs: CaseStudy
) -> tp.Dict[str, tp.Dict[int, tp.List[tp.Tuple[str, str, float]]]]:
    str_val_map = create_config_opportunities_value_map(cs)

    full_data = aggregate_data(cs, None)

    config_ids = full_data["config_id"].unique()

    result = {}

    for metrics in full_data["metric"].unique():

        result[metrics] = defaultdict(dict)

        for config_id in config_ids:
            result[metrics][config_id] = []

            config_data = full_data[(full_data["config_id"] == config_id) &
                                    (full_data["metric"] == metrics)]

            for wl in config_data["binary-wl"].unique():
                wl_data = config_data[config_data["binary-wl"] == wl]

                baseline_data = wl_data[wl_data["config_opportunity"] ==
                                        "__baseline__"]["value"].tolist()[0]

                for config_opportunity in wl_data["config_opportunity"].unique(
                ):
                    if config_opportunity == "__baseline__":
                        continue

                    config_opportunity_data = wl_data[
                        wl_data["config_opportunity"] == config_opportunity]

                    for variation in config_opportunity_data["variation"
                                                            ].unique():
                        variation_data = config_opportunity_data[
                            config_opportunity_data["variation"] == variation
                        ]["value"].tolist()[0]

                        ttest_res = ttest_ind(baseline_data, variation_data)

                        if ttest_res.pvalue > 0.05:
                            continue

                        print(
                            f"{metrics} {config_id} {wl} {config_opportunity} {variation} {ttest_res.pvalue}"
                        )
                        print(f"{baseline_data} {variation_data}")

                        rel_data = config_opportunity_data[
                            config_opportunity_data["variation"] == variation
                        ]["value_relative"].tolist()[0]

                        print(f"{rel_data}")

                        result[metrics][config_id].append((
                            wl, config_opportunity,
                            str_val_map[config_opportunity][variation]
                        ))

    return result


class EffectSize(float, Enum):
    NONE = 0.0
    VERY_SMALL = 0.01
    SMALL = 0.2
    MEDIUM = 0.5
    LARGE = 0.8
    VERY_LARGE = 1.2
    HUGE = 2.0

    @staticmethod
    def interpret(effect_size: float) -> 'EffectSize':
        effect_size = abs(effect_size)
        if effect_size < EffectSize.VERY_SMALL.value:
            return EffectSize.NONE
        if effect_size < EffectSize.SMALL.value:
            return EffectSize.VERY_SMALL
        if effect_size < EffectSize.MEDIUM.value:
            return EffectSize.SMALL
        if effect_size < EffectSize.LARGE.value:
            return EffectSize.MEDIUM
        if effect_size < EffectSize.VERY_LARGE.value:
            return EffectSize.LARGE
        if effect_size < EffectSize.HUGE.value:
            return EffectSize.VERY_LARGE
        else:
            return EffectSize.HUGE
