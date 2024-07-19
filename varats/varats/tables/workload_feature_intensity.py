import typing as tp

from varats.data.reports.workload_feature_intensity_report import (
    WorkloadFeatureIntensityReport,
)
from varats.experiments.vara.workload_feature_intensity import (
    WorkloadFeatureIntensityExperiment,
)
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.tables import TableFormat, TableGenerator


class WorkloadIntensityTable(Table, table_name="workload_intensity"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_study: CaseStudy = self.table_kwargs.pop("case_study")

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

            reports = WorkloadFeatureIntensityReport(
                report_files[0].full_path()
            )

            for report in reports.reports():
                pass

        pass


class WorkloadIntensityTableGenerator(
    TableGenerator, generator_name="workload-intensity", options=[]
):

    def generate(self) -> tp.List[Table]:
        case_studies = get_loaded_paper_config().get_all_case_studies()
        return [
            WorkloadIntensityTable(
                self.table_config, case_study=cs, **self.table_kwargs
            ) for cs in case_studies if cs.project_name == "SynthCTCRTP"
        ]
