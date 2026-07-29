import pandas as pd

from varats.data.databases.hidden_configurability_database import (
    aggregate_data_for_cs,
    calculate_kruskal_wallis_summary,
)
from varats.experiments.vara.hidden_configurability_experiments import (
    _PROJECT_WORKLOADS,
)
from varats.paper.paper_config import get_loaded_paper_config
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.tables.hc_latex_table_constants import reformat_project_column


class HCPerfSensitivityTable(Table, table_name="hc_perf_sensitivity"):
    """
    Table to display sensitivity results.

    Shows the performance sensitivity of the hidden configurability subjects to
    changes in the configuration. The table includes the following columns:
    - Subject: The name of the subject system.
    - # Settings: The number of configuration settings for the subject system.
    - # Alternatives: The number of alternatives tested for the subject system.
    - #SigSettings: The number of significant settings where Kruskal-Wallis
     test showed significant differences in performance.
    - #SigAlternatives: The number of significant alternatives where Kruskal-Wallis
        test showed significant differences in performance.
    - MinRangeSettings(pp): The minimum performance range observed across all significant settings.
    - MaxRangeSettings(pp): The maximum performance range observed across all significant settings.
    - MinRangeAlternatives(pp): The minimum performance range observed across all significant alternatives.
    - MaxRangeAlternatives(pp): The maximum performance range observed across all significant alternatives.
    """

    def _style_for_latex(self, df):
        kwargs: dict = {
            "hrules": True,
            "label": "tab:results_rq2",
            "caption": r"Summary of results for \RQref{2}. For each subject "
                       r"system, we report the number of instances where we "
                       r"found significant differences across alternatives "
                       r"($\symSig^{2.1}_{\symProject}$) within a setting for"
                       r" \RQref{2.1} and across settings "
                       r"($\symSig^{2.2}_{\symProject}$) within an alternative "
                       r"for \RQref{2.2}. In addition, we report the relative "
                       r"share with respect to all settings and all alternatives."
                       r" We also report the performance range in percentage "
                       r"points observed across all significant settings "
                       r"($\symRange^{2.1}_{\symProject}$) and alternatives "
                       r"($\symRange^{2.2}_{\symProject}$)",
        }

        # Format the columns:
        #   min_setting_range
        #   max_setting_range
        #   min_config_alt_range
        #   max_config_alt_range
        # Such that:
        # - They are multiplied by 100 with 2 decimal places
        # - iff the value is < 1, simply show "< 1".
        # - Iff the value is nan, simply show "-"
        for col in [
            "min_setting_range",
            "max_setting_range",
            "min_config_alt_range",
            "max_config_alt_range",
        ]:
            df[col] = df[col].apply(
                lambda x: f"{x*100:.2f}" if pd.notna(x) and x >= 0.01 else (
                    "< 1" if pd.notna(x) else "-"
                )
            )

        # Merge min and max range columns to one column with format: "min -- max"
        df["setting_range"] = df.apply(
            lambda row: f"{row['min_setting_range']} -- {row['max_setting_range']}"
            if pd.notna(row["min_setting_range"]) and pd.notna(row["max_setting_range"])
            else "-",
            axis=1
        )
        df["config_alt_range"] = df.apply(
            lambda row: f"{row['min_config_alt_range']} -- {row['max_config_alt_range']}"
            if pd.notna(row["min_config_alt_range"]) and pd.notna(row["max_config_alt_range"])
            else "-",
            axis=1
        )

        # Drop the original min and max range columns and reorder the columns to have the new range columns at the end
        df = df.drop(
            columns=[
                "min_setting_range",
                "max_setting_range",
                "min_config_alt_range",
                "max_config_alt_range",
            ]
        )

        # Format the sig columns to also show the relative share with respect to all settings and alternatives in parentheses
        df["num_sig_settings"] = df.apply(
            lambda row: f"{row['num_sig_settings']} ({row['num_sig_settings'] / row['num_settings_total']:.2%})"
            if row["num_settings"] > 0 else r"---"
            , axis=1
        )

        df["num_sig_config_alts"] = df.apply(
            lambda row: f"{row['num_sig_config_alts']} ({row['num_sig_config_alts'] / row['num_config_alts_total']:.2%})"
            if row["num_config_alts"] > 0 else r"---"
            , axis=1
        )

        # Debug print to show projects and number of settings/alternatives
        print(f"{df[['project', 'num_settings_total', 'num_config_alts_total']]}")

        df = df[
            [
                "project",
#                "num_settings",
                "num_sig_settings",
                "setting_range",
#                "num_config_alts",
                "num_sig_config_alts",
                "config_alt_range",
            ]
        ]

        # Column formats:
        kwargs["column_format"] = r"lrrrr"

        df = reformat_project_column(df)

        # Rename columns:
        df = df.rename(columns={
            "project": "",
            #"num_settings": r"$\symSettings^{2}_{\symProject}$",
            "num_sig_settings": r"$\symSig^{2.1}_{\symProject}$",
            "setting_range": r"$\symRange^{2.1}_{\symProject}$",
            #"num_config_alts": r"$\symAlts^{2}_{\symProject}$",
            "num_sig_config_alts": r"$\symSig^{2.2}_{\symProject}$",
            "config_alt_range": r"$\symRange^{2.2}_{\symProject}$",
        }).set_index("")

        return df, kwargs


    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        full_data = pd.DataFrame()

        for cs in case_studies:
            if cs.project_name not in _PROJECT_WORKLOADS:
                print(
                    f"Skipping {cs.project_name} as it is not "
                    f"an active HV subject system"
                )
                continue
            print(f"Processing {cs.project_name}...")

            cs_data = aggregate_data_for_cs(cs, None)
            cs_data["project"] = cs.project_name
            full_data = pd.concat([full_data, cs_data], ignore_index=True)

        kruskal_results = calculate_kruskal_wallis_summary(full_data)

        kwargs = {}
        if table_format==TableFormat.LATEX:
            kruskal_results, kwargs = self._style_for_latex(kruskal_results)

        return dataframe_to_table(kruskal_results, table_format,
                                  wrap_table=wrap_table, **kwargs)

class HCPerfSensitivityTableGenerator(TableGenerator,
                                      generator_name="hc_perf_sensitivity",
                                      options=[]):
    """Generator for the HCPerfSensitivityTable."""

    def generate(self) -> list[Table]:
        return [HCPerfSensitivityTable(self.table_config, **self.table_kwargs)]