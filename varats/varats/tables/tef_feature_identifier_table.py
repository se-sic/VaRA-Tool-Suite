import math
import typing as tp

import pandas as pd

from varats.data.reports.tef_feature_identifier_report import (
    TEFFeatureIdentifierReport,
)
from varats.experiments.vara.tef_region_identifier import TEFFeatureIdentifier
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableGenerator, TableFormat


class TEFFeatureIdentifierTable(Table, table_name="tef-feature-id"):
    """Table that compares the precision of different feature performance
    measurement approaches."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        project_name: str = self.table_kwargs['case_study'].project_name
        cs = self.table_kwargs['case_study']

        report_files = get_processed_revisions_files(
            project_name,
            TEFFeatureIdentifier,
            TEFFeatureIdentifierReport,
            get_case_study_file_name_filter(cs),
            only_newest=False
        )

        table_rows = []

        for report_path in report_files:
            report = TEFFeatureIdentifierReport(report_path.full_path())
            config_id = report_path.report_filename.config_id

            for patch in report.patch_names:
                new_row = {}
                for region in report.regions_for_patch(patch):
                    if "__VARA__DETECT__" in region[0]:
                        r = list(region[0].difference({"__VARA__DETECT__"}))
                        if len(r) == 0:
                            r.append("Base")
                        new_row["*".join(r)] = region[1]

                if all([new_row[r] == 0 for r in new_row]):
                    continue

                new_row['Name'] = patch
                new_row['ConfigId'] = config_id

                table_rows.append(new_row)

        row_setup = [[], []]
        for row in table_rows:
            row_setup[0].append(row['Name'])
            row_setup[1].append(row['ConfigId'])

        df = pd.DataFrame(table_rows, index=row_setup)
        df.sort_values(['Name', 'ConfigId'], inplace=True)
        df.fillna(0, inplace=True)
        df.drop(labels=['Name', 'ConfigId'], axis=1, inplace=True)

        print(f"{df=}")

        style: pd.io.formats.style.Styler = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["hrules"] = True
            kwargs["convert_css"] = True
            kwargs[
                "caption"
            ] = f"""Overview table for {project_name} of the ground truth experiment. The column names list the affected feature names.
            If a patch has an effect on a specific configuration ID, we list how often a feature is affected.
                """

            column_format = "ll|" + ("c" * len(df.columns))
            kwargs["column_format"] = column_format
            style.format(precision=0)

        return dataframe_to_table(
            df,
            table_format,
            wrap_table=wrap_table,
            style=style,
            wrap_landscape=True,
            **kwargs
        )


class TEFFeatureIdentifierTableGenerator(
    TableGenerator, generator_name="tef-feature-id", options=[]
):
    """Generator for `FeaturePerfPrecisionTable`."""

    def generate(self) -> tp.List[Table]:
        return [
            TEFFeatureIdentifierTable(
                self.table_config, **self.table_kwargs, case_study=cs
            ) for cs in get_loaded_paper_config().get_all_case_studies()
        ]
