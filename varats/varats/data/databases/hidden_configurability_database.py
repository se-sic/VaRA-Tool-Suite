import ast
import typing as tp
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ttest_ind

from varats.data.cache_helper import cache_dataframe, load_cached_df_or_none
from varats.data.reports.hidden_configurability_report import MPRTimeWLAggregate
from varats.experiments.base.run_workloads import RunWorkloads
from varats.experiments.hidden_config.benchbase_experiments import (
    BenchbaseHiddenConfig,
    MPBenchbaseReport,
)
from varats.experiments.hidden_config.hidden_config_utils import (
    get_all_variations_as_dict,
)
from varats.experiments.vara.hidden_configurability_experiments import (
    TimePatchedWorkloads,
    variation_value_to_str,
)
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.projects.cpp_projects.libzmq import LibZMQMPReport
from varats.report.gnu_time_report import WLTimeReportAggregate
from varats.revision.revisions import get_processed_revisions_files

CACHE_DATA_ID = "hc_database"


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


def get_data_for_single_config(
    cs: CaseStudy, config_id: tp.Optional[int] = None
) -> pd.DataFrame:
    # Case distinction for specific projects
    if cs.project_name == "libzmq":
        df1 = _get_data_single_config_default(cs, config_id)
        # Change all occurrences of config_opportunity "hwm" to "sndbuf"
        df1.loc[df1["config_opportunity"] == "default_hwm",
                "config_opportunity"] = "hwm"

        df2 = _get_data_single_config_libzmq(cs, config_id)
        return pd.concat([df1, df2], ignore_index=True)

    if cs.project_name in ["mariadb", "postgresql", "mysql"]:
        return _get_data_single_config_benchbase(cs, config_id)

    return _get_data_single_config_default(cs, config_id)


def _get_data_single_config_libzmq(
    cs, config_id: tp.Optional[int] = None
) -> pd.DataFrame:
    # Load all result files from RunAllWorkloads experiment
    result_files = get_processed_revisions_files(
        "libzmq",
        RunWorkloads,
        RunWorkloads.report_spec().main_report,
        get_case_study_file_name_filter(cs),
        config_id=config_id,
        only_newest=False,
    )

    if len(result_files) == 0:
        print(f"No results found for {cs.project_name} ({config_id=})")
        return pd.DataFrame()

    data_rows = []
    base_values = {}

    for result_file in result_files:
        # Load report as LibZMQMPReport
        report: LibZMQMPReport = LibZMQMPReport(result_file.full_path())

        # Parse base reports
        for base_report in report.all_baseline_reports():
            if "inproc_lat" in base_report.filename.filename:
                metric = "latency"
                data_rows.append({
                    "binary-wl": f"bench-inproc-lat",
                    "config_opportunity": "__baseline__",
                    "variation": None,
                    "metric": metric,
                    "value": base_report.latencies,
                    "config_id": config_id,
                })

                base_values[metric] = np.mean(base_report.latencies)
            elif "inproc_thr" in base_report.filename.filename:
                data_rows.extend([{
                    "binary-wl": f"bench-inproc-thr",
                    "config_opportunity": "__baseline__",
                    "variation": None,
                    "metric": "throughput_msg",
                    "value": base_report.throughputs_msg,
                    "config_id": config_id
                }, {
                    "binary-wl": f"bench-inproc-thr",
                    "config_opportunity": "__baseline__",
                    "variation": None,
                    "metric": "throughput_mb",
                    "value": base_report.throughputs_mb,
                    "config_id": config_id
                }])

                base_values["throughput_msg"] = np.mean(
                    base_report.throughputs_msg
                )
                base_values["throughput_mb"] = np.mean(
                    base_report.throughputs_mb
                )

        def extract_variation(patch_name: str) -> str:
            # patch names follow the pattern "<patch_name>_<base_file_name>_<config_point>=<value>"
            # We want to extract <value>
            name_path = Path(patch_name).stem
            split_leftover_fn = name_path.partition("_")
            config_part = split_leftover_fn[-1]
            config_point = config_part.split('=')
            return config_point[1]

        for patch_name in report.get_patch_names():
            patched_report = report.get_report_for_patch(patch_name)

            variation = extract_variation(patch_name)

            if "inproc_lat" in patched_report.filename.filename:
                metric = "latency"
                data_rows.append({
                    "binary-wl": f"bench-inproc-lat",
                    "config_opportunity": "hwm",
                    "variation": variation,
                    "metric": metric,
                    "value": patched_report.latencies,
                    "value_relative": [(t / base_values[metric]) - 1
                                       for t in patched_report.latencies],
                    "config_id": config_id,
                })
            elif "inproc_thr" in patched_report.filename.filename:
                data_rows.extend([{
                    "binary-wl": f"bench-inproc-thr",
                    "config_opportunity": "hwm",
                    "variation": variation,
                    "metric": "throughput_msg",
                    "value": patched_report.throughputs_msg,
                    "value_relative": [(t / base_values["throughput_msg"]) - 1
                                       for t in patched_report.throughputs_msg],
                    "config_id": config_id
                }, {
                    "binary-wl": f"bench-inproc-thr",
                    "config_opportunity": "hwm",
                    "variation": variation,
                    "metric": "throughput_mb",
                    "value": patched_report.throughputs_mb,
                    "value_relative": [(t / base_values["throughput_mb"]) - 1
                                       for t in patched_report.throughputs_mb],
                    "config_id": config_id
                }])

        result = pd.DataFrame.from_records(data_rows)

        return result


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

    if cs.project_name == "DunePerfRegression":
        result_files = [
            rf for rf in result_files if "yasp_q2_3d" in str(rf.full_path())
        ]

    data_rows = []

    base_times = {}
    base_rss = {}

    for result_file in result_files:
        report: MPRTimeWLAggregate = MPRTimeWLAggregate(result_file.full_path())

        binary = report.filename.binary_name

        base_report: WLTimeReportAggregate = report.get_baseline_report()

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

        for patch_report in report.get_patched_reports():
            cp = extract_config_point(patch_report.filename.filename)

            for wl in patch_report.workload_names():
                data_rows.extend([{
                    "binary-wl": f"{binary}/{wl}",
                    "config_opportunity": f"{cp[0]}",
                    "variation": cp[1].strip("_"),
                    "metric": "wall_clock_time",
                    "value": patch_report.measurements_wall_clock_time(wl),
                    "value_relative": [
                        (t / base_times[wl]) - 1
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
                        (t / base_rss[wl]) - 1
                        for t in patch_report.max_resident_sizes(wl)
                    ],
                    "config_id": report.filename.config_id,
                }])

    result = pd.DataFrame.from_records(data_rows)

    return result


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
        "goodput": {},
    }

    for result_file in result_files:
        report: MPBenchbaseReport = MPBenchbaseReport(result_file.full_path())
        binary = report.filename.binary_name

        patch_names = report.get_patch_names()

        for base_name in report.get_base_names():
            baseline_report = report.get_baseline_for(base_name)

            if baseline_report is None:
                continue

            data_rows.extend([
                # TODO: Latencies?
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
                    "metric": "goodput",
                    "value": baseline_report.summary(base_name).goodput,
                    "value_relative": None,
                    "config_id": report.filename.config_id,
                }
            ])

            base_data["throughput"][base_name] = np.mean(
                baseline_report.summary(base_name).throughput
            )
            base_data["goodput"][base_name] = np.mean(
                baseline_report.summary(base_name).goodput
            )

            for patch_name in patch_names:
                patched_report = report.get_patched_for(base_name, patch_name)

                if patched_report is None:
                    continue

                cp = patch_name.split("=")[0], patch_name.split("=")[-1]

                data_rows.extend([{
                    "binary-wl": f"{binary}/{base_name}",
                    "config_opportunity": f"{cp[0]}",
                    "variation": cp[1],
                    "metric": "throughput",
                    "value": patched_report.summary(base_name).throughput,
                    "value_relative": [
                        (t / base_data["throughput"][base_name]) - 1
                        for t in patched_report.summary(base_name).throughput
                    ],
                    "config_id": report.filename.config_id,
                }, {
                    "binary-wl": f"{binary}/{base_name}",
                    "config_opportunity": f"{cp[0]}",
                    "variation": cp[1],
                    "metric": "goodput",
                    "value": patched_report.summary(base_name).goodput,
                    "value_relative": [
                        (t / base_data["goodput"][base_name]) - 1
                        for t in patched_report.summary(base_name).goodput
                    ],
                    "config_id": report.filename.config_id,
                }])

    result = pd.DataFrame.from_records(data_rows)
    return result


def _load_cached_df(project_name: str):
    dtypes = {
        "binary-wl": "str",
        "config_opportunity": "str",
        "variation": "str",
        "metric": "str",
        "value": "str",
        "value_relative": "str",
        "config_id": "Int64",
    }
    df = load_cached_df_or_none(CACHE_DATA_ID, project_name, dtypes)

    if df is None:
        return None

    # Convert columns "value" and "value_relative" back to lists
    df["value"] = df["value"].apply(lambda x: ast.literal_eval(x))
    df["value_relative"] = df["value_relative"].apply(
        lambda x: ast.literal_eval(x)
    )

    return df


def _cache_df(df: pd.DataFrame, project_name: str):
    # Convert columns "value" and "value_relative" to string to store lists in csv
    df["value"] = df["value"].apply(lambda x: str(x))
    df["value_relative"] = df["value_relative"].apply(lambda x: str(x))

    cache_dataframe(CACHE_DATA_ID, project_name, df)


def aggregate_data(
    cs: CaseStudy, config_ids: tp.Optional[tp.List[int]]
) -> pd.DataFrame:

    result_df = _load_cached_df(cs.project_name)

    if result_df is None:
        # Data not cached, load from reports and cache it for future use
        result_df = pd.DataFrame()

        if config_ids is None:
            config_ids = cs.get_config_ids_for_revision(cs.revisions[0])

        if len(config_ids) == 0:
            config_ids = [None]

        for config_id in config_ids:
            config_df = get_data_for_single_config(cs, config_id)

            result_df = pd.concat([result_df, config_df], ignore_index=True)

        _cache_df(result_df, cs.project_name)

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
                                         row["config_id"]][0]
        return ttest_ind(baseline_value, row["value"])

    df["significance"] = df.apply(is_significant, axis=1)

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
