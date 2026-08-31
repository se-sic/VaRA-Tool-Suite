"""Module for the FeaturePerfPrecision tables."""
import typing as tp
import pandas as pd
from varats.data.reports.instrumentation_verifier_report import InstrVerifierReport
from varats.experiments.vara.feature_weight import WeightRegionsCountRec
from varats.experiments.vara.feature_weight_default import WeightRegionsCountDef
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator


class FeatureWeightAnalysisTable(Table,
                                 table_name="fperf-weight"):
    """Table that compares the different type of weight analysis."""

    @staticmethod
    def _prepare_data_table(
        case_studies: tp.List[CaseStudy]
    ) -> pd.DataFrame:
        df = pd.DataFrame()
        table_rows = []

        for case_study in case_studies:
            reports_rec = get_processed_revisions_files(
                case_study.project_name,
                WeightRegionsCountRec,
                InstrVerifierReport,
                get_case_study_file_name_filter(case_study),
            )

            report_file = reports_rec[0]
            rec_report = InstrVerifierReport(report_file.full_path())

            reports_def = get_processed_revisions_files(
                case_study.project_name,
                WeightRegionsCountDef,
                InstrVerifierReport,
                get_case_study_file_name_filter(case_study),
            )
            report_file = reports_def[0]
            base_report = InstrVerifierReport(report_file.full_path())
            # add the base reports
            row = {
                "Project": case_study.project_name,
                "Base": base_report.num_enters_total(),
                "Recursive": rec_report.num_enters_total(),
            }

            table_rows.append(row)


        return pd.concat([df, pd.DataFrame(table_rows)])

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """Setup performance precision table."""
        case_studies = get_loaded_paper_config().get_all_case_studies()

        # Data aggregation
        df = self._prepare_data_table(case_studies)

        return dataframe_to_table(
            df,
            table_format,
            wrap_table=wrap_table,
            wrap_landscape=True
        )

class FeatureWeightAnalysisGenerator(
    TableGenerator, generator_name="fperf-weight", options=[]
):
    """Generator for `FeatureWeightAnalysisTable`."""

    def generate(self) -> tp.List[Table]:
        return [
            FeatureWeightAnalysisTable(self.table_config, **self.table_kwargs)
        ]
