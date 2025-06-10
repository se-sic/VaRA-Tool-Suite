import typing as tp
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy.stats import ttest_ind

from varats.data.reports.hidden_configurability_report import MPRTimeWLAggregate
from varats.experiments.vara.hidden_configurability_experiments import (
    TimePatchedWorkloads,
    PATCH_VARIATIONS,
    variation_value_to_str,
)
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.gnu_time_report import WLTimeReportAggregate
from varats.revision.revisions import get_processed_revisions_files


def extract_config_point(full_name: str) -> tp.Tuple[str, str]:
    # patch names follow the pattern "<patch_name>_<base_file_name>_<config_point>=<value>"
    # We are interested in the unique configuration points
    name_parts = full_name.split("_")
    config_point = name_parts[-1].split("=")
    return config_point[0], config_point[1].split('.')[0]


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

        def get_shortname(name: str) -> str:
            name = name.split("/")[-1]  # Get the last part of the path
            fn_without_prefix = name[len("patched_"):]
            split_leftover_fn = fn_without_prefix.partition("_")
            shortname_length = int(split_leftover_fn[0])
            patch_shortname = "".join(split_leftover_fn[2:])[:shortname_length]
            return patch_shortname

        for patch_report in report.get_patched_reports():
            cp = extract_config_point(patch_report.filename.filename)
            patch_name = get_shortname(patch_report.filename.filename)

            for wl in patch_report.workload_names():
                data_rows.extend([{
                    "binary-wl": f"{binary}/{wl}",
                    "config_opportunity": f"{patch_name}/{cp[0]}",
                    "variation": cp[1],
                    "metric": "wall_clock_time",
                    "value": patch_report.measurements_wall_clock_time(wl),
                    "value_relative": [
                        (t / base_times[wl]) - 1
                        for t in patch_report.measurements_wall_clock_time(wl)
                    ],
                    "config_id": report.filename.config_id,
                }, {
                    "binary-wl": f"{binary}/{wl}",
                    "config_opportunity": f"{patch_name}/{cp[0]}",
                    "variation": cp[1],
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

    str_val_map = create_config_opportunities_value_map(cs)

    def map_str_values(row: pd.Series) -> pd.Series:
        """Map string values to numerical values."""
        if row["config_opportunity"] == "__baseline__":
            return row
        row["variation"] = str_val_map[row["config_opportunity"]][str(
            row["variation"]
        )]
        return row

    result_df = result_df.apply(map_str_values, axis=1)

    return result_df


def create_config_opportunities_value_map(
    cs: CaseStudy
) -> tp.Dict[str, tp.Dict[str, float]]:
    """Create a mapping of configuration opportunities to their values."""
    result = {}

    patches = PATCH_VARIATIONS[cs.project_name]

    for patch_name, config_opportunity in patches.items():
        arg_name, values = config_opportunity
        result[f'{patch_name}/{arg_name.replace("_", "-")}'] = {
            variation_value_to_str(value): value for value in values
        }

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
                                         row["config_id"]]
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
