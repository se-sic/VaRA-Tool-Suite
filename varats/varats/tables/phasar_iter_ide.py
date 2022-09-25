import typing as tp

import numpy as np
import pandas as pd

from varats.data.reports.phasar_iter_ide import PhasarIterIDEStatsReport
from varats.experiments.phasar.iter_ide import (
    IDELinearConstantAnalysisExperiment,
)
from varats.jupyterhelper.file import load_phasar_iter_ide_stats_report
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.project.project_util import (
    get_local_project_git,
    get_project_cls_by_name,
)
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table, TableDataEmpty
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.utils.git_util import calc_repo_loc


def from_kbytes_to_mbytes(kbytes: int) -> int:
    return kbytes / 1000


class PhasarIterIDEStats(Table, table_name="phasar-iter-ide-stats"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        cs_data: tp.List[pd.DataFrame] = []

        for case_study in get_loaded_paper_config().get_all_case_studies():
            print(f"Working on {case_study}")
            project_name = case_study.project_name
            report_files = get_processed_revisions_files(
                case_study.project_name, IDELinearConstantAnalysisExperiment,
                PhasarIterIDEStatsReport,
                get_case_study_file_name_filter(case_study)
            )
            print(f"{report_files=}")

            revision = None
            revisions = case_study.revisions
            if len(revisions) == 1:
                revision = revisions[0]

            rev_range = revision.hash if revision else "HEAD"

            for report_file in report_files:
                report = load_phasar_iter_ide_stats_report(report_file)
                project_cls = get_project_cls_by_name(project_name)
                project_repo = get_local_project_git(project_name)
                if not report.basic_bc_stats:
                    raise TableDataEmpty(
                        "Stats file was not present in the report."
                    )

                typestate_time = np.nan
                typestate_mem = np.nan
                if report.old_typestate:
                    typestate_time = report.old_typestate.wall_clock_time\
                        .total_seconds()
                    typestate_mem = from_kbytes_to_mbytes(
                        report.old_typestate.max_res_size
                    )

                taint_time = np.nan
                taint_mem = np.nan
                if report.old_taint:
                    taint_time = report.old_taint.wall_clock_time.total_seconds(
                    )
                    taint_mem = from_kbytes_to_mbytes(
                        report.old_taint.max_res_size
                    )

                lca_time = np.nan
                lca_mem = np.nan
                if report.old_lca:
                    lca_time = report.old_lca.wall_clock_time.total_seconds()
                    lca_mem = from_kbytes_to_mbytes(report.old_lca.max_res_size)

                cs_dict = {
                    project_name: {
                        "Revision":
                            str(revision.short_hash),
                        "Domain":
                            str(project_cls.DOMAIN)[0].upper() +
                            str(project_cls.DOMAIN)[1:],
                        "LOC":
                            calc_repo_loc(project_repo, rev_range),
                        "IR-LOC":
                            report.basic_bc_stats.num_instructions,
                        "Typestate-T":
                            typestate_time,
                        "Typestate-M":
                            typestate_mem,
                        "Taint-T":
                            taint_time,
                        "Taint-M":
                            taint_mem,
                        "LCA-T":
                            lca_time,
                        "LCA-M":
                            lca_mem,
                    }
                }

                cs_data.append(pd.DataFrame.from_dict(cs_dict, orient="index"))

        if len(cs_data) == 0:
            raise TableDataEmpty()

        df = pd.concat(cs_data).sort_index()
        print(df)
        print(df.columns)

        df.columns = pd.MultiIndex.from_tuples([
            ('', 'Revision'),
            ('', 'Domain'),
            ('', 'LOC'),
            ('', 'IR-LOC'),
            ('Typestate', 'Time (s)'),
            ('Typestate', 'Mem (mbytes)'),
            ('Taint', 'Time (s)'),
            ('Taint', 'Mem (mbytes)'),
            ('LCA', 'Time (s)'),
            ('LCA', 'Mem (mbytes)'),
        ])

        print(df)

        style = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            # df.style.format('j')
            kwargs["column_format"] = "lr|crr|rr|rr|rr"
            kwargs["multicol_align"] = "c|"
            # kwargs["multicolumn"] = True
            kwargs['position'] = 't'
            kwargs[
                "caption"
            ] = """On the left, we see all evaluted projectes with additional information, such as, revision we analyzed, the amount of C/C++ code. The three columns on the right show time and memory consumption of the benchmarked analyses utilizing the current version of the IDE solver."""
            style.format(precision=2)

        return dataframe_to_table(
            df,
            table_format,
            style,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class PhasarIterIDEStatsGenerator(
    TableGenerator, generator_name="phasar-iter-ide-stats", options=[]
):
    """TODO: """

    def generate(self) -> tp.List[Table]:
        return [PhasarIterIDEStats(self.table_config, **self.table_kwargs)]
