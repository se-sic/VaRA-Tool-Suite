import typing as tp

import numpy as np
import pandas as pd
from pylatex import Document

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
from varats.report.gnu_time_report import TimeReportAggregate
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table, TableDataEmpty
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.utils.git_util import calc_repo_loc


def from_kbytes_to_mbytes(kbytes: float) -> float:
    return kbytes / 1000.


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
                    typestate_time = np.mean(
                        report.old_typestate.measurements_wall_clock_time
                    )
                    typestate_mem = from_kbytes_to_mbytes(
                        np.mean(report.old_typestate.max_resident_sizes)
                    )

                taint_time = np.nan
                taint_mem = np.nan
                if report.old_taint:
                    taint_time = np.mean(
                        report.old_taint.measurements_wall_clock_time
                    )
                    taint_mem = from_kbytes_to_mbytes(
                        np.mean(report.old_taint.max_resident_sizes)
                    )

                lca_time = np.nan
                lca_mem = np.nan
                if report.old_lca:
                    lca_time = np.mean(
                        report.old_lca.measurements_wall_clock_time
                    )
                    lca_mem = from_kbytes_to_mbytes(
                        np.mean(report.old_lca.max_resident_sizes)
                    )

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

        memory_limit = 100000  # mbytes

        style: pd.io.formats.style.Styler = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            style.highlight_between(
                left=memory_limit,
                props='cellcolor:{red};',
                subset=[('Typestate', 'Mem (mbytes)'),
                        ('Taint', 'Mem (mbytes)'), ('LCA', 'Mem (mbytes)')]
            )
            # df.style.format('j')
            kwargs["column_format"] = "lr|crr|rr|rr|rr"
            kwargs["multicol_align"] = "c|"
            # kwargs["multicolumn"] = True
            kwargs['position'] = 't'
            kwargs[
                "caption"
            ] = f"""On the left, we see all evaluted projectes with additional information, such as, revision we analyzed, the amount of C/C++ code.
The three columns on the right show time and memory consumption of the benchmarked analyses utilizing the current version of the IDE solver.
The red cells indicate that our memory limit of {memory_limit} mbytes was exceeded."""
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


class PhasarIterIDEOldVSNew(Table, table_name="phasar-iter-ide-old-new"):

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

                cs_dict = {project_name: {}}
                cs_dict[project_name].update(
                    self.compute_typestate_stats(report)
                )
                cs_dict[project_name].update(self.compute_taint(report))
                cs_dict[project_name].update(self.compute_lca_stats(report))
                cs_data.append(pd.DataFrame.from_dict(cs_dict, orient="index"))

        df = pd.concat(cs_data).sort_index()

        print(df)

        style: pd.io.formats.style.Styler = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs[
                "column_format"
            ] = "l|cccp{0.7cm}|cccp{0.7cm}|cccp{0.7cm}|cccp{0.7cm}|cccp{0.7cm}|cccp{0.7cm}|"
            kwargs["multicol_align"] = "c|"
            # kwargs["multicolumn"] = True
            kwargs['position'] = 't'
            kwargs["caption"] = """Foo bar"""
            style.format(precision=2)

        def add_extras(doc: Document) -> None:
            pass

        return dataframe_to_table(
            df,
            table_format,
            style,
            wrap_table=wrap_table,
            wrap_landscape=True,
            document_decorator=add_extras,
            **kwargs
        )

    def compute_typestate_stats(self, report: PhasarIterIDEStatsReport):
        return self.__compute_delta_comp(
            "Typestate", report.old_typestate, report.new_typestate
        )

    def compute_taint(self, report: PhasarIterIDEStatsReport):
        return self.__compute_delta_comp(
            "Taint", report.old_taint, report.new_taint
        )

    def compute_lca_stats(self, report: PhasarIterIDEStatsReport):
        return self.__compute_delta_comp("LCA", report.old_lca, report.new_lca)

    def __compute_delta_comp(
        self, name: str, old_time_report: tp.Optional[TimeReportAggregate],
        new_time_report: tp.Optional[TimeReportAggregate]
    ):
        time_old = np.nan
        time_new = np.nan
        time_speedup = np.nan
        time_variance = np.nan

        memory_old = np.nan
        memory_new = np.nan
        memory_speedup = np
        memory_variance = np.nan

        if old_time_report:
            time_old = np.mean(old_time_report.measurements_wall_clock_time)
            memory_old = from_kbytes_to_mbytes(
                np.mean(old_time_report.max_resident_sizes)
            )

        if new_time_report:
            time_new = np.mean(new_time_report.measurements_wall_clock_time)
            memory_new = from_kbytes_to_mbytes(
                np.mean(new_time_report.max_resident_sizes)
            )

        time_speedup = time_old / time_new
        memory_speedup = memory_old / memory_new

        if old_time_report and new_time_report:
            t1 = np.var(old_time_report.measurements_wall_clock_time)
            t2 = np.var(new_time_report.measurements_wall_clock_time)
            t1 = round(t1, 2)
            t2 = round(t2, 2)
            time_variance = f'{t1} | {t2}'
            print(f"{np.var(old_time_report.max_resident_sizes)=}")
            m1 = from_kbytes_to_mbytes(
                np.var(old_time_report.max_resident_sizes)
            )
            m2 = from_kbytes_to_mbytes(
                np.var(new_time_report.measurements_wall_clock_time)
            )
            m1 = round(m1, 2)
            m2 = round(m2, 2)
            memory_variance = f'{m1} | {m2}'

        return {(name, 'Time', 'Old'): time_old,
                (name, 'Time', 'New'): time_new,
                (name, 'Time', '$\mathcal{S}$'): time_speedup,
                (name, 'Time', '$s^2$'): time_variance,
                (name, 'Memory', 'Old'): memory_old,
                (name, 'Memory', 'New'): memory_new,
                (name, 'Memory', '$\mathcal{S}$'): memory_speedup,
                (name, 'Memory', '$s^2$'): memory_variance}


class PhasarIterIDEOldVSNewGenerator(
    TableGenerator, generator_name="phasar-iter-ide-old-new", options=[]
):
    """TODO: """

    def generate(self) -> tp.List[Table]:
        return [PhasarIterIDEOldVSNew(self.table_config, **self.table_kwargs)]
