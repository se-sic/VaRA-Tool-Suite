import numpy as np
import pandas as pd

from varats.data.databases.hidden_configurability_database import (
    ACTIVE_HV_PROJECTS,
    EffectSize,
    aggregate_data_for_cs,
    filter_for_significant_changes,
    get_all_data,
)
from varats.experiments.vara.hidden_configurability_experiments import (
    _PROJECT_WORKLOADS,
)
from varats.paper.paper_config import get_loaded_paper_config
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.tables.hc_latex_table_constants import reformat_project_column


def _extract_significance_data_for_subset(
    data: pd.DataFrame,
    field_value: str,
    field_name: str = "config_opportunity",
) -> dict:
    result = {
        "num_variations": 0,
        "num_sig_impacts": 0,
        "num_pos_sig_impacts": 0,
        "num_neg_sig_impacts": 0,
        "min_impact": None,
        "max_impact": None,
    }

    opportunity_data = data[
        data[field_name] == field_value]

    # Filter all rows where the significance pvalue is < 0.05
    # Each row has a object where the pvalue is stored in a
    # field named pvalue
    significant_impacts = filter_for_significant_changes(opportunity_data)

    result["num_variations"] = len(
        opportunity_data["variation"].unique()
    )

    result["num_sig_impacts"] = len(significant_impacts)
    if not significant_impacts.empty:
        means = significant_impacts["value_relative"].apply(
            np.mean
        )
        result["num_pos_sig_impacts"] = int((means > 0).sum())
        result["num_neg_sig_impacts"] = int((means < 0).sum())

        result["min_impact"] = means.min()
        result["max_impact"] = means.max()

        # Debug Print: Show the rows with highest and lowest mean impact
        print("Most positive significant impact:")
        print(significant_impacts.loc[means.idxmax()])
        print("Most negative significant impact:")
        print(significant_impacts.loc[means.idxmin()])

        # Add overview of effect sizes
        # Effect size categories are in the "effect_size" column
        for effect_size in EffectSize:
            result[f"ES_{effect_size.name}"] = (
                int((significant_impacts["effect_size"] ==
                                              effect_size).sum()))

    return result

class HCPerfDetailTable(Table, table_name="hc_perf_detail"):
    """
    HC Performance impacts in great detail by setting, configuration alternative, metric, and case study.

    'The big table that knows everything' - Lukas
    """
    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """Tabulates the HC Performance Detail Table."""
        df = get_all_data()

        # If there is anything in "value_relative", aggregate it to a mean value
        df["value_relative"] = df["value_relative"].apply(
            lambda x: np.mean(x) if isinstance(x, list) else x
        )

        return dataframe_to_table(df, table_format, wrap_table=wrap_table)

class HCPerfMetricsSummaryTable(Table, table_name="hc_perf_metrics_summary"):
    """
    HC Performance impacts by metric and case study.

    For each case study and metric, we summarize the performance impacts of all
     configuration opportunities. We report the number of alternatives (|A|),
     the number of significant performance impacts (|S|),
     the number of significant positive impacts (|S+|),
     the number of significant negative impacts (|S-|),
     and the range of performance impacts (min, max).
    """
    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:  # noqa: PLR0912
        """Tabulates the HC Performance Summary Table."""
        case_studies = get_loaded_paper_config().get_all_case_studies()

        table_rows = []

        for cs in case_studies:
            if cs.project_name not in ACTIVE_HV_PROJECTS:
                print(
                    f"Skipping {cs.project_name} as it is not "
                    f"an active HV subject system"
                )
                continue
            print(f"Processing {cs.project_name}...")
            # Filter to single config ID for projects with multiple
            __cs_configs = {
                "libzmq": [13],
                "FastDownward": [0],
                "libvpx": [0],
            }
            if cs.project_name in __cs_configs:
                config_id = __cs_configs[cs.project_name][0]
            else:
                config_id = None
            try:
                cs_data = aggregate_data_for_cs(cs, [config_id])
            except Exception as e:  # noqa: BLE001
                print(f"Error processing {cs.project_name}: {e}")
                continue

            # For each row, we want to summarize the performance impact
            # of all configuration opportunities

            # Columns: Project Name, |A| (Number of alternatives),
            # Metric, |S| (Number of significant performance impacts),
            # |S+| (Number of significant positive impacts),
            # |S-| (Number of significant negative impacts),
            # Impact Range (min, max)

            # For simplicity, we only consider one workload per project here
            workload = _PROJECT_WORKLOADS[cs.project_name][0]

            if cs_data.empty:
                continue

            if cs.project_name == "libzmq":
                # Special case for libzmq as the workload names are inconsistent
                workload = "bench-inproc"

            # Filter CS datat based on bianry-wl column
            # No exact string match possible so we test if
            # workload is a substring
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
                    "|S-|": 0,
                    "|S+|": 0,
                    "Range": (None, None),
                }

                for es in EffectSize:
                    new_row[f"ES({es.name})"] = 0

                for config_opportunity in metric_data["config_opportunity"
                                                     ].unique():

                    sig_data = _extract_significance_data_for_subset(
                        metric_data, config_opportunity
                    )

                    new_row["|A|"] += sig_data["num_variations"]
                    new_row["|S|"] += sig_data["num_sig_impacts"]
                    new_row["|S+|"] += sig_data["num_pos_sig_impacts"]
                    new_row["|S-|"] += sig_data["num_neg_sig_impacts"]
                    if sig_data["min_impact"] is not None:
                        new_row["Range"] = (
                            min(new_row["Range"][0], sig_data["min_impact"])
                            if new_row["Range"][0] is not None
                            else sig_data["min_impact"],
                            max(new_row["Range"][1], sig_data["max_impact"])
                            if new_row["Range"][1] is not None
                            else sig_data["max_impact"]
                        )

                    for es in EffectSize:
                        new_row[f"ES({es.name})"] += sig_data.get(f"ES_{es.name}"
                                                                  , 0)

                # Convert Impact Range to normal floats
                new_row["Range"] = (
                    float(new_row["Range"][0]) if new_row["Range"][0]
                    is not None else "N/A", float(new_row["Range"][1])
                    if new_row["Range"][1] is not None else "N/A"
                )

                table_rows.append(new_row)

        df = pd.DataFrame(table_rows).set_index("Name")

        # Convert Range column to percentages
        def format_range(
            range_tuple: tuple[float | str, float | str]
        ) -> str:
            if range_tuple[0] == "N/A" or range_tuple[1] == "N/A":
                return "N/A"
            return f"({range_tuple[0]:.2%}, {range_tuple[1]:.2%})"

        df = df.sort_index()
        df["Range"] = df["Range"].apply(format_range)

        # Convert effect sizes to relative numbers
        for es in EffectSize:
            df[f"ES({es.name})"] = df[f"ES({es.name})"] / df["|S|"]

            df[f"ES({es.name})"] = df[f"ES({es.name})"].apply(
                lambda x: f"{x:.2%}" if isinstance(x, float) else x
            )

        # Temp: Drop range
        df = df.drop(columns=[f"ES({e.name})" for e in EffectSize])

        #Convert ES columns to multi-index
        #df.columns = pd.MultiIndex.from_tuples(
        #    [("EffectSize", col.split("(")[1][:-1]) if
        #    "(" in col else ("", col)
        #    for col in df.columns]
        #)

        return dataframe_to_table(df, table_format, wrap_table=wrap_table)


class HCPerfMetricsSummaryGenerator(
    TableGenerator, generator_name="hc_perf_metrics_summary", options=[]
):
    """Generator for the HC Performance Summary Table."""

    def generate(self) -> list[Table]:
        """Generates the HC Performance Summary Table."""
        return [
            HCPerfMetricsSummaryTable(self.table_config, **self.table_kwargs)
        ]
class HCPerfSummaryTable(Table, table_name="hc_perf_summary"):
    """
    HC Performance impacts by configuration opportunity and case study.

    For each case study and configuration opportunity, we summarize the
    performance impacts of the configuration opportunity.
    We report, for each subject system:
    - The name of the subject system
    - The total number of alternatives across all opportunitites (|A|)
    - The number of settings considered (|S|)
    - The total number of significant performance impacts (|I|)
    - The number of significant positive impacts (|I+|)
    - The number of significant negative impacts (|I-|)
    - The range of performance impacts (min, max)
    """
    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """Tabulates the HC Performance Summary Table."""
        case_studies = get_loaded_paper_config().get_all_case_studies()

        table_rows = []

        for cs in case_studies:
            if cs.project_name not in _PROJECT_WORKLOADS:
                print(
                    f"Skipping {cs.project_name} as it is not "
                    f"an active HV subject system"
                )
                continue
            print(f"Processing {cs.project_name}...")

            # Gather data for all config IDs of the current case study
            #try:
            cs_data = aggregate_data_for_cs(cs, None)
            #except Exception as e:  # noqa: BLE001
                #print(f"Error processing {cs.project_name}: {e}")
                #continue

            if cs_data.empty:
                # Add dummy row with N/A values for all metrics
                table_rows.append({
                    "Name": cs.project_name,
                    #"|O|": None,
                    "|A|": None,
                    "|S|": None,
                    "|P|": None,
                    "|I|": None,
                    "|I+|": None,
                    "|I-|": None,
                    "Range": ("N/A", "N/A"),
                })
                continue

            # Filter out baseline rows
            cs_data = cs_data[cs_data["config_opportunity"] != "__baseline__"]

            num_opportunities = cs_data["config_opportunity"].nunique()
            # Settings are the unique combinations of configurations, metrics, and workloads
            num_settings = cs_data[["config_id", "metric", "binary-wl"]].drop_duplicates().shape[0]

            new_row = {
                "Name": cs.project_name,
                #"|O|": num_opportunities,
                "|A|": 0,
                "|S|": num_settings,
                "|P|": len(cs_data),
                "|I|": 0,
                "|I+|": 0,
                "|I-|": 0,
                "Range": (None, None),
            }

            # Iterate over each configuration opportunity
            for config_opportunity in cs_data["config_opportunity"].unique():
                sig_data = _extract_significance_data_for_subset(
                    cs_data, config_opportunity
                )
                new_row["|A|"] += sig_data["num_variations"]
                new_row["|I|"] += sig_data["num_sig_impacts"]
                new_row["|I+|"] += sig_data["num_pos_sig_impacts"]
                new_row["|I-|"] += sig_data["num_neg_sig_impacts"]
                if sig_data["min_impact"] is not None:
                    new_row["Range"] = (
                        min(new_row["Range"][0], sig_data["min_impact"])
                        if new_row["Range"][0] is not None
                        else sig_data["min_impact"],
                        max(new_row["Range"][1], sig_data["max_impact"])
                        if new_row["Range"][1] is not None
                        else sig_data["max_impact"]
                    )

            # Convert Impact Range to normal floats
            new_row["Range"] = (
                float(new_row["Range"][0]) if new_row["Range"][0] is not None
                else "N/A", float(new_row["Range"][1]) if new_row["Range"][1]
                is not None else "N/A"
            )

            table_rows.append(new_row)

        df = pd.DataFrame(table_rows)
        df = df.sort_values(by="Name")

        kwargs = {}
        if table_format == TableFormat.LATEX:
            reformat_project_column(df, column_name="Name")
            df = df.set_index("Name")

            def format_range(
                    range_tuple: tuple[float | str, float | str]
            ) -> str:
                if range_tuple[0] == "N/A" or range_tuple[1] == "N/A":
                    return "N/A"
                return f"{range_tuple[0]:+.1%} -- {range_tuple[1]:+.1%}"

            # Escape percent signs in the Range column for LaTeX
            df["Range"] = (df["Range"].apply(format_range)
                           .apply(lambda x: x.replace("%", r"\%") if isinstance(x, str) else x))

            # Reformat number columns to have half spaces for 1000s
            for col in ["|A|", "|S|", "|P|", "|I|", "|I+|", "|I-|"]:
                df[col] = df[col].apply(
                    lambda x: f"{x:,}".replace(",", r"\,") if isinstance(x, int) else x
                )

            df = df.rename(columns={
                #"|O|": r"$|\symOpportunities_{\symProject}|$",
                "|A|": r"$|\symAlternatives_{\symProject}|$",
                "|S|": r"$|\symSettings_{\symProject}|$",
                "|I|": r"%|\symNumSig{}|%",
                "|I+|": r"%|\symNumSigPos{}|%",
                "|I-|": r"$|\symNumSigNeg{}|$",
                "|P|": r"$|\symMeasurements{}{}{\symProject}|$",
                "Range": "Impact Range"
            },
            index={"Name": ""})

            kwargs["hrules"] = True
            kwargs["column_format"] = "lrrrrrrr"
            kwargs[
                "caption"
            ] = (r"Summary of our findings for \RQref{1}."
                 r" For each project we list the total number of alternatives"
                 r" considered (\symNumAlts{}) and report for each metric the"
                 r" total number significant findings (\symNumSig{}),"
                 r" as well as the number of findings with an overall positive"
                 r" impact (\symNumSigPos{}) and negative impact"
                 r" (\symNumSigNeg{}) on the mean of the metric. In addition, "
                 r"we report the minimum and maximum mean performance change "
                 r"across all significant changes.")
            kwargs["label"] = "tab:rq1_summary"
        else:
            # Convert Range column to percentages
            # Prepend + sign to positive numbers for better readability
            def format_range(
                    range_tuple: tuple[float | str, float | str]
            ) -> str:
                if range_tuple[0] == "N/A" or range_tuple[1] == "N/A":
                    return "N/A"
                return f"({range_tuple[0]:+.1%}, {range_tuple[1]:+.1%})"

            df["Range"] = df["Range"].apply(format_range)

        return dataframe_to_table(df, table_format, wrap_table=wrap_table, **kwargs)

class HCPerfSummaryGenerator(
    TableGenerator, generator_name="hc_perf_summary", options=[]
):
    """Generator for the HC Performance Summary Table."""

    def generate(self) -> list[Table]:
        """Generates the HC Performance Summary Table."""
        return [HCPerfSummaryTable(self.table_config, **self.table_kwargs)]

def _generate_table_data(table_kwargs,fields):
    case_study = table_kwargs.get("case_study")
    if not case_study:
        raise ValueError("case_study argument is required for this table")

    cs_data = aggregate_data_for_cs(case_study, None)
    if cs_data.empty:
        raise ValueError(f"No data found for case study {case_study.project_name}")

    return cs_data[fields].drop_duplicates().sort_values(
        by=fields).set_index(fields[0])

class SettingIDMappingTable(
    Table, table_name="setting-id-mapping"
):
    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """Tabulates the HC Setting ID Mapping Table."""
        df = _generate_table_data(self.table_kwargs, ["setting_id", "binary-wl", "config_id", "metric"])

        return dataframe_to_table(df, table_format, wrap_table=wrap_table)

class ConfAltIDMappingTable(
    Table, table_name="confalt-id-mapping"
):
    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """Tabulates the HC Setting ID Mapping Table."""
        df = _generate_table_data(self.table_kwargs, ["config_alt_id", "config_opportunity", "variation"])

        return dataframe_to_table(df, table_format, wrap_table=wrap_table)

class SettingIDMappingGenerator(
    TableGenerator, generator_name="hc_setting_id_mappings", options=[
    ]
):
    """Generator for the HC Setting ID Mapping Table."""

    def generate(self) -> list[Table]:
        """Generates the HC Setting ID Mapping Table."""
        case_studies = get_loaded_paper_config().get_all_case_studies()

        case_studies = [cs for cs in case_studies if cs.project_name in _PROJECT_WORKLOADS]

        return [SettingIDMappingTable(self.table_config, case_study=cs, **self.table_kwargs) for cs in case_studies]

class ConfAltIDMappingGenerator(
    TableGenerator, generator_name="hc_config_alt_id_mappings", options=[
    ]
):
    """Generator for the HC Setting ID Mapping Table."""

    def generate(self) -> list[Table]:
        """Generates the HC Setting ID Mapping Table."""
        case_studies = get_loaded_paper_config().get_all_case_studies()

        case_studies = [cs for cs in case_studies if cs.project_name in _PROJECT_WORKLOADS]

        return [ConfAltIDMappingTable(self.table_config, case_study=cs, **self.table_kwargs) for cs in case_studies]
