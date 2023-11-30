import typing as tp

import pandas as pd

from varats.data.reports.tef_feature_identifier_report import TEFFeatureIdentifierReport

from varats.experiments.vara.tef_region_identifier import TEFFeatureIdentifier

from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableGenerator, TableFormat, TableConfig


class TEFFeatureIdentifierTable(Table, table_name="tef-feature-id"):
    """Table that compares the precision of different feature performance
    measurement approaches."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        project_name: str = self.table_kwargs['case_study'].project_name
        cs = self.table_kwargs['case_study']

        report_files = get_processed_revisions_files(
            cs,
            TEFFeatureIdentifier,
            TEFFeatureIdentifierReport,
            get_case_study_file_name_filter(cs)
        )

        table_rows = []

        for report_path in report_files:
            report = TEFFeatureIdentifierReport(report_path.full_path())
            config_id = report_path.report_filename.config_id

            new_row = {
                'Name': "__Baseline",
                'ConfigId' : config_id
            }
            for region in report.baseline_regions:
                r = region[0].difference({"__VARA__DETECT__"})
                new_row["*".join(r)] = region[1]

            table_rows.append(new_row)

            for patch in report.patch_names:
                new_row = {
                    'Name': patch,
                    'ConfigId': config_id
                }
                for region in report.regions_for_patch(patch):
                    if "__VARA__DETECT__" in region[0]:
                        r = region[0].difference({"__VARA__DETECT__"})
                        new_row["*".join(r)] = region[1]

                table_rows.append(new_row)

        df = pd.DataFrame(table_rows)
        df.sort_values(['ConfigId', 'Name'])

        return dataframe_to_table(
            df,
            table_format,
            wrap_table=wrap_table,
            wrap_landscape=True
        )


class TEFFeatureIdentifierTableGenerator(
    TableGenerator, generator_name="tef-feature-id", options=[]
):
    """Generator for `FeaturePerfPrecisionTable`."""

    def generate(self) -> tp.List[Table]:
        return [
            TEFFeatureIdentifierTable(self.table_config, **self.table_kwargs, case_study=cs)
            for cs in get_loaded_paper_config().get_all_case_studies()
        ]
