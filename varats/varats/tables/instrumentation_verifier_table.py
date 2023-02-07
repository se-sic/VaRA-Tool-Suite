"""Generates tables for the instrumentation verifier experiment status for all
case studies in the paper config."""

import typing as tp

import numpy as np
import pandas as pd

import varats.paper.paper_config as PC
from varats.data.reports.instrumentation_verifier_report import (
    InstrVerifierReport,
)
from varats.experiments.vara.instrumentation_verifier import RunInstrVerifier
from varats.revision.revisions import get_all_revisions_files
from varats.table.table import Table, TableDataEmpty
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator


class InstrumentationVerifierTable(
    Table, table_name="instrumentation_verifier_table"
):
    """
    Generates a table for the instrumentation verifier experiment status for a
    specific case study.

    Each traced binary of the case study is listed with its current state, the
    number of enters and leaves, the number of unclosed enters and the number of
    unentered leaves.
    """

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        variables = [
            "Workload name", "State", "ConfigID", "#Enters", "#Leaves",
            "#Unclosed Enters", "#Unentered Leaves"
        ]

        experiment_type = RunInstrVerifier
        project_name: str = self.table_kwargs['case_study'].project_name

        data = []

        revision_files = get_all_revisions_files(
            project_name, experiment_type, only_newest=False
        )

        reports = [
            InstrVerifierReport(rev_file.full_path())
            for rev_file in revision_files
        ]

        for report in reports:
            for binary in report.binaries():
                data.append([
                    f"{report.filename.commit_hash} - {binary}",
                    report.state(binary), report.filename.config_id,
                    report.num_enters(binary),
                    report.num_leaves(binary),
                    report.num_unclosed_enters(binary),
                    report.num_unentered_leaves(binary)
                ])

        if len(data) == 0:
            raise TableDataEmpty()

        pd_data = pd.DataFrame(columns=variables, data=np.array(data))

        return dataframe_to_table(
            pd_data, table_format, wrap_table=wrap_table, wrap_landscape=True
        )


class InstrVerifierTableGenerator(
    TableGenerator, generator_name="instrumentation-verifier-table", options=[]
):
    """Generates an overview table for the instrumentation verifier
    experiment."""

    def generate(self) -> tp.List[Table]:
        return [
            InstrumentationVerifierTable(
                self.table_config, case_study=cs, **self.table_kwargs
            ) for cs in PC.get_paper_config().get_all_case_studies()
        ]
