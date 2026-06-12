import pandas as pd

from varats.data.databases.hidden_configurability_database import aggregate_data, calculate_kruskal_wallis
from varats.paper.paper_config import get_loaded_paper_config
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.experiments.vara.hidden_configurability_experiments import (
    _PROJECT_WORKLOADS,
)


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
    """

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

            cs_data = aggregate_data(cs, None)
            cs_data["project"] = cs.project_name
            full_data = pd.concat([full_data, cs_data], ignore_index=True)

        kruskal_results = calculate_kruskal_wallis(full_data)

        return dataframe_to_table(kruskal_results, table_format, wrap_table=wrap_table)

class HCPerfSensitivityTableGenerator(TableGenerator,
                                      generator_name="hc_perf_sensitivity",
                                      options=[]):
    """Generator for the HCPerfSensitivityTable."""

    def generate(self) -> list[Table]:
        return [HCPerfSensitivityTable(self.table_config, **self.table_kwargs)]