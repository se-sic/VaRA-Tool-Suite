import typing as tp

import numpy as np
import pandas as pd

import varats.paper.paper_config as PC
from varats.data.reports.instrumentation_verifier_report import (
    InstrVerifierReport,
)
from varats.experiments.vara.instrumentation_verifier import RunInstrVerifier
from varats.revision.revisions import get_all_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator


class InstrumentationVerifierTable(
    Table, table_name="instrumentation_verifier_table"
):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        variables = [
            "Case Study", "#Traced Binaries", "#Enters", "#Leaves",
            "#Unclosed Enters", "#Unentered Leaves"
        ]

        current_config = PC.get_paper_config()
        experiment_type = RunInstrVerifier
        data = []
        for case_study in current_config.get_all_case_studies():
            revision_files = get_all_revisions_files(
                case_study.project_name, experiment_type, only_newest=False
            )

            reports = [
                InstrVerifierReport(rev_file.full_path())
                for rev_file in revision_files
            ]

            data.append([
                case_study.project_name,
                len(revision_files),
                sum(report.num_enters() for report in reports),
                sum(report.num_leaves() for report in reports),
                sum(report.num_unclosed_enters() for report in reports),
                sum(report.num_unentered_leave() for report in reports)
            ])

        pddata = pd.DataFrame(columns=variables, data=np.array(data))

        return dataframe_to_table(
            pddata, table_format, wrap_table=wrap_table, wrap_landscape=True
        )


class InstrVerifierTableGenerator(
    TableGenerator, generator_name="instrumentation-verifier-table", options=[]
):
    """Generates an overview table for the instrumentation verifier
    experiment."""

    def generate(self) -> tp.List[Table]:
        # TODO: Add option to differ between aggregating all binaries for one CS
        #  , or create separate tables per CS with each binary representing one row
        return [
            InstrumentationVerifierTable(
                self.table_config, **self.table_kwargs
            )
        ]
