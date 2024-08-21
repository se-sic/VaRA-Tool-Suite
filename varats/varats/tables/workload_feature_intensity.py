import typing as tp

import pandas as pd

from varats.data.reports.workload_feature_intensity_report import (
    WorkloadFeatureIntensityReport,
    feature_region_string_from_set,
)
from varats.experiments.vara.workload_feature_intensity import (
    WorkloadFeatureIntensityExperiment,
)
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator


class WorkloadIntensityTable(Table, table_name="workload_intensity"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_study: CaseStudy = self.table_kwargs.pop("case_study")

        table_rows = []

        for config_id in case_study.get_config_ids_for_revision(
            case_study.revisions[0]
        ):
            project_name = case_study.project_name
            report_files = get_processed_revisions_files(
                project_name,
                WorkloadFeatureIntensityExperiment,
                WorkloadFeatureIntensityReport,
                get_case_study_file_name_filter(case_study),
                config_id=config_id
            )

            if len(report_files) > 1:
                raise AssertionError("Should only be one")
            if not report_files:
                print(
                    f"Could not find workload intensity data for {project_name=}"
                    f". {config_id=}"
                )
                return None

            report = WorkloadFeatureIntensityReport(report_files[0].full_path())

            for binary in report.binaries():
                for workload, intensities in report.feature_intensities_for_binary(
                    binary
                ).items():
                    new_row = {
                        "Config": config_id,
                        "Binary": binary,
                        "Workload": workload
                    }

                    new_row.update({
                        feature_region_string_from_set(feature): intensity
                        for feature, intensity in intensities.items()
                    })

                    table_rows.append(new_row)

        df = pd.DataFrame(table_rows)

        # Use MultiIndex to group by binary and workload
        df.set_index(["Binary", "Workload"], inplace=True)

        # Replace NaN values with 0
        df.fillna(0, inplace=True)

        # Sort by workload name
        df.sort_index(inplace=True)

        return dataframe_to_table(df, table_format, wrap_table=wrap_table)


class WorkloadIntensityTableGenerator(
    TableGenerator, generator_name="workload-intensity", options=[]
):

    def generate(self) -> tp.List[Table]:
        case_studies = get_loaded_paper_config().get_all_case_studies()
        return [
            WorkloadIntensityTable(
                self.table_config, case_study=cs, **self.table_kwargs
            )
            for cs in case_studies
            if cs.project_name == "WorkloadFeatureIntensity"
        ]
