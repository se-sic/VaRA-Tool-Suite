import typing as tp

import pandas as pd

from varats.data.reports.feature_instrumentation_points_report import (
    FeatureInstrumentationPointsReport,
)
from varats.data.reports.workload_feature_intensity_report import (
    WorkloadFeatureIntensityReport,
    feature_region_string_from_set,
)
from varats.experiments.vara.feature_instrumentation_points import (
    FeatureInstrumentationPoints,
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
            intensity_report_files = get_processed_revisions_files(
                project_name,
                WorkloadFeatureIntensityExperiment,
                WorkloadFeatureIntensityReport,
                get_case_study_file_name_filter(case_study),
                config_id=config_id
            )

            instrumentation_points_report_files = get_processed_revisions_files(
                project_name,
                FeatureInstrumentationPoints,
                FeatureInstrumentationPointsReport,
                get_case_study_file_name_filter(case_study),
                config_id=config_id
            )

            if len(intensity_report_files) > 1:
                raise AssertionError("Should only be one")
            if not intensity_report_files or not instrumentation_points_report_files:
                print(
                    f"Could not find workload intensity data for {project_name=}"
                    f". {config_id=}"
                )
                return None

            intensity_report = WorkloadFeatureIntensityReport(
                intensity_report_files[0].full_path()
            )

            for binary in intensity_report.binaries():
                if not any([
                    ipr.report_filename.binary_name == binary
                    for ipr in instrumentation_points_report_files
                ]):
                    print(
                        f"Could not find a matching instrumentation points report for {binary=} ({config_id=}).\n"
                        f"Skipping binary."
                    )
                    continue

                ipr_file = [
                    ipr for ipr in instrumentation_points_report_files
                    if ipr.report_filename.binary_name == binary
                ][0]
                instrumentation_points_report = FeatureInstrumentationPointsReport(
                    ipr_file.full_path()
                )

                for workload, intensities in intensity_report.feature_intensities_for_binary(
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

                    for feature in instrumentation_points_report.feature_names(
                    ):
                        all_region_uuids = instrumentation_points_report.regions_for_feature(
                            feature
                        )
                        region_intensities = intensity_report.region_intensities_for_binary(
                            binary
                        )[workload]

                        encountered_region_uuids = set()

                        for feature_names in region_intensities:
                            if not feature in feature_names:
                                continue

                            for region_uuids in region_intensities[feature_names
                                                                  ]:
                                encountered_region_uuids.update([
                                    uuid for uuid in region_uuids
                                    if instrumentation_points_report.
                                    feature_name_for_region(uuid) == feature
                                ])

                        new_row[
                            f"ER({feature})"
                        ] = f"{len(encountered_region_uuids)} / {len(all_region_uuids)}"

                    table_rows.append(new_row)

        df = pd.DataFrame(table_rows)

        # Rearrange columns for better readability
        column_names = ["Binary", "Workload", "Config"]
        column_names += [col for col in df.columns if col.startswith("FR(")]
        column_names += sorted([
            col for col in df.columns if col.startswith("ER(")
        ])
        df = df[column_names]

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
