import typing as tp

import click
import pandas as pd

from varats.data.databases.hidden_configurability_database import aggregate_data
from varats.experiments.hidden_config.hidden_config_utils import (
    get_all_variations_as_dict,
)
from varats.paper.paper_config import get_loaded_paper_config
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.cli_util import make_cli_option


class ConfigOpportunitiesSignificanceTable(
    Table, table_name="config_opportunities_significance"
):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()
        metric = self.table_kwargs["metric"]

        table_data = []

        for case_study in case_studies:
            cs_data = aggregate_data(case_study, None)

            if cs_data.empty:
                print(f"No data for {case_study.project_name}")
                continue

            cs_data = cs_data[(cs_data["metric"] == metric) &
                              (cs_data["config_opportunity"] != "__baseline__")]

            row = {
                "cs": case_study.project_name,
                "|C|": len(cs_data["config_id"].unique()),
                "|W|": len(cs_data["binary-wl"].unique()),
            }

            num_variations = 0

            for patch, arg in get_all_variations_as_dict(case_study).items():
                _, values = arg
                num_variations += len(values)

            row["|VP|"] = num_variations

            row["|A|"] = num_variations * row["|W|"] * row["|C|"]

            sig_df = cs_data[cs_data.apply(
                lambda x: x["significance"].pvalue < 0.05, axis=1
            )]
            row["#Significant"] = sig_df.shape[0]
            row["Significant (%)"] = row["#Significant"] / row["|A|"] * 100

            table_data.append(row)

        df = pd.DataFrame(table_data)

        df.sort_values(by="cs", inplace=True)

        return dataframe_to_table(df, table_format, wrap_table=wrap_table)


class ConfigOpportunitiesSignificanceTableGenerator(
    TableGenerator,
    generator_name="config-opportunities-significance",
    options=[
        make_cli_option(
            "--metric",
            type=click.Choice(["wall_clock_time", "max_resident_size"]),
            required=True,
            help="Metric to plot (e.g. wall_clock_time,max_resident_size)",
        )
    ]
):
    """Table generator for the ConfigOpportunitiesSignificanceTable."""

    def generate(self) -> tp.List[Table]:
        return [
            ConfigOpportunitiesSignificanceTable(
                self.table_config, **self.table_kwargs
            )
        ]
