import typing as tp

import numpy as np
import pandas as pd

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
                "config_id": report.filename.config_id,
            }, {
                "binary-wl": f"{binary}/{wl}",
                "config_opportunity": "__baseline__",
                "variation": None,
                "metric": "max_resident_size",
                "value": base_report.max_resident_sizes(wl),
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
                    "config_opportunity": cp[0],
                    "variation": cp[1],
                    "metric": "wall_clock_time",
                    "value": patch_report.measurements_wall_clock_time(wl),
                    "config_id": report.filename.config_id,
                }, {
                    "binary-wl": f"{binary}/{wl}",
                    "config_opportunity": cp[0],
                    "variation": cp[1],
                    "metric": "max_resident_size",
                    "value": patch_report.max_resident_sizes(wl),
                    "config_id": report.filename.config_id,
                }, {
                    "binary-wl":
                        f"{binary}/{wl}",
                    "config_opportunity":
                        cp[0],
                    "variation":
                        cp[1],
                    "metric":
                        "wall_clock_time_relative",
                    "value": (
                        np.mean(patch_report.measurements_wall_clock_time(wl)) /
                        base_times[wl]
                    ) - 1,
                    "config_id":
                        report.filename.config_id,
                }, {
                    "binary-wl":
                        f"{binary}/{wl}",
                    "config_opportunity":
                        cp[0],
                    "variation":
                        cp[1],
                    "metric":
                        "max_resident_size_relative",
                    "value": (
                        np.mean(patch_report.max_resident_sizes(wl)) /
                        base_rss[wl]
                    ) - 1,
                    "config_id":
                        report.filename.config_id,
                }])

    result = pd.DataFrame.from_records(data_rows)

    return result


def aggregate_date(cs: CaseStudy, config_ids: tp.List[int]) -> pd.DataFrame:
    result_df = pd.DataFrame()

    for config_id in config_ids:
        config_df = get_data_for_single_config(cs, config_id)

        result_df = pd.concat([result_df, config_df], ignore_index=True)

    return result_df


def create_config_opportunities_value_map(
    cs: CaseStudy
) -> tp.Dict[str, tp.Dict[str, float]]:
    """Create a mapping of configuration opportunities to their values."""
    result = {}

    patches = PATCH_VARIATIONS[cs.project_name]

    for patch_name, config_opportunity in patches.items():
        arg_name, values = config_opportunity
        result[arg_name.replace("_", "-")] = {
            variation_value_to_str(value): value for value in values
        }

    return result
