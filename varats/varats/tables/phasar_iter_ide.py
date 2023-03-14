import itertools
import typing as tp

import numpy as np
import pandas as pd
from pylatex import Document, NoEscape, Package

from varats.data.reports.phasar_iter_ide import (
    PhasarIterIDEStatsReport,
    ResultCompare,
)
from varats.experiments.phasar.iter_ide import (
    IDELinearConstantAnalysisExperiment,
)
from varats.jupyterhelper.file import load_phasar_iter_ide_stats_report
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
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


def latex_sanitize_project_name(project_name: str) -> str:
    return project_name.replace('_', '\_')


def from_kbytes_to_mbytes(kbytes: float) -> float:
    return kbytes / 1000.


def all_from_kbytes_to_mbytes(kbytes_list: tp.List[float]) -> tp.List[float]:
    return list(map(from_kbytes_to_mbytes, kbytes_list))


def get_compare_mark(res_cmp: tp.Optional[ResultCompare]) -> str:
    if not res_cmp:
        return "{\color{RedOrange} ?}"

    if res_cmp.results_match:
        return "{\color{Green} \checkmark}"

    return "{\color{Red} x}"


class PhasarIterIDEStats(Table, table_name="phasar-iter-ide-stats"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        cs_data: tp.List[pd.DataFrame] = []

        for case_study in get_loaded_paper_config().get_all_case_studies():
            print(f"Working on {case_study.project_name}")
            project_name = case_study.project_name
            report_files = get_processed_revisions_files(
                case_study.project_name, IDELinearConstantAnalysisExperiment,
                PhasarIterIDEStatsReport,
                get_case_study_file_name_filter(case_study)
            )
            # print(f"{report_files=}")

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
                    latex_sanitize_project_name(project_name): {
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

        cluster_memory_limit = 128000  # mbytes
        dev_memory_limit = 32000  # mbytes

        style: pd.io.formats.style.Styler = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            style.highlight_between(
                left=cluster_memory_limit,
                props='cellcolor:{red};',
                subset=[('Typestate', 'Mem (mbytes)'),
                        ('Taint', 'Mem (mbytes)'), ('LCA', 'Mem (mbytes)')]
            )
            style.highlight_between(
                left=dev_memory_limit,
                right=cluster_memory_limit,
                props='cellcolor:{orange};',
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
The orange cells indicate that the memory of a usual developer maschine ({dev_memory_limit} mbytes) was exceeded and the red cells indicate that even a compute cluster with {cluster_memory_limit} mbytes would be not enough."""
            style.format(precision=2)

        return dataframe_to_table(
            df,
            table_format,
            style,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class PhasarIterIDEStatsWL(Table, table_name="phasar-iter-ide-stats-wl"):

    def get_time_and_mem(self, report_entry):
        time = np.nan
        mem = np.nan
        if report_entry:
            time = np.mean(report_entry.measurements_wall_clock_time)
            mem = from_kbytes_to_mbytes(
                np.mean(report_entry.max_resident_sizes)
            )
        return (time, mem)

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        cs_data: tp.List[pd.DataFrame] = []

        for case_study in get_loaded_paper_config().get_all_case_studies():
            print(f"Working on {case_study.project_name}")
            project_name = case_study.project_name
            report_files = get_processed_revisions_files(
                case_study.project_name, IDELinearConstantAnalysisExperiment,
                PhasarIterIDEStatsReport,
                get_case_study_file_name_filter(case_study)
            )
            # print(f"{report_files=}")

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

                typestate_time_stack, typestate_mem_stack = self.get_time_and_mem(
                    report.new_typestate_stack
                )
                typestate_time_queue, typestate_mem_queue = self.get_time_and_mem(
                    report.new_typestate_queue
                )
                typestate_time_size_prio, typestate_mem_size_prio = self.get_time_and_mem(
                    report.new_typestate_size_prio
                )
                typestate_time_size_prio_rev, typestate_mem_size_prio_rev = self.get_time_and_mem(
                    report.new_typestate_size_prio_rev
                )
                typestate_time_depth_prio, typestate_mem_depth_prio = self.get_time_and_mem(
                    report.new_typestate_depth_prio
                )
                typestate_time_depth_prio_rev, typestate_mem_depth_prio_rev = self.get_time_and_mem(
                    report.new_typestate_depth_prio_rev
                )

                taint_time_stack, taint_mem_stack = self.get_time_and_mem(
                    report.new_taint_stack
                )
                taint_time_queue, taint_mem_queue = self.get_time_and_mem(
                    report.new_taint_queue
                )
                taint_time_size_prio, taint_mem_size_prio = self.get_time_and_mem(
                    report.new_taint_size_prio
                )
                taint_time_size_prio_rev, taint_mem_size_prio_rev = self.get_time_and_mem(
                    report.new_taint_size_prio_rev
                )
                taint_time_depth_prio, taint_mem_depth_prio = self.get_time_and_mem(
                    report.new_taint_depth_prio
                )
                taint_time_depth_prio_rev, taint_mem_depth_prio_rev = self.get_time_and_mem(
                    report.new_taint_depth_prio_rev
                )

                lca_time_stack, lca_mem_stack = self.get_time_and_mem(
                    report.new_lca_stack
                )
                lca_time_queue, lca_mem_queue = self.get_time_and_mem(
                    report.new_lca_queue
                )
                lca_time_size_prio, lca_mem_size_prio = self.get_time_and_mem(
                    report.new_lca_size_prio
                )
                lca_time_size_prio_rev, lca_mem_size_prio_rev = self.get_time_and_mem(
                    report.new_lca_size_prio_rev
                )
                lca_time_depth_prio, lca_mem_depth_prio = self.get_time_and_mem(
                    report.new_lca_depth_prio
                )
                lca_time_depth_prio_rev, lca_mem_depth_prio_rev = self.get_time_and_mem(
                    report.new_lca_depth_prio_rev
                )

                cs_dict = {
                    latex_sanitize_project_name(project_name): {
                        "Revision":
                            str(revision.short_hash),
                        "Domain":
                            str(project_cls.DOMAIN)[0].upper() +
                            str(project_cls.DOMAIN)[1:],
                        "LOC":
                            calc_repo_loc(project_repo, rev_range),
                        "IR-LOC":
                            report.basic_bc_stats.num_instructions,
                        "Typestate-Stack-T":
                            typestate_time_stack,
                        "Typestate-Stack-M":
                            typestate_mem_stack,
                        "Typestate-Queue-T":
                            typestate_time_queue,
                        "Typestate-Queue-M":
                            typestate_mem_queue,
                        "Typestate-Size-Prio-T":
                            typestate_time_size_prio,
                        "Typestate-Size-Prio-M":
                            typestate_mem_size_prio,
                        "Typestate-Size-Prio-Reversed-T":
                            typestate_time_size_prio_rev,
                        "Typestate-Size-Prio-Reversed-M":
                            typestate_mem_size_prio_rev,
                        "Typestate-Depth-Prio-T":
                            typestate_time_depth_prio,
                        "Typestate-Depth-Prio-M":
                            typestate_mem_depth_prio,
                        "Typestate-Depth-Prio-Reversed-T":
                            typestate_time_depth_prio_rev,
                        "Typestate-Depth-Prio-Reversed-M":
                            typestate_mem_depth_prio_rev,
                        "Taint-Stack-T":
                            taint_time_stack,
                        "Taint-Stack-M":
                            taint_mem_stack,
                        "Taint-Queue-T":
                            taint_time_queue,
                        "Taint-Queue-M":
                            taint_mem_queue,
                        "Taint-Size-Prio-T":
                            taint_time_size_prio,
                        "Taint-Size-Prio-M":
                            taint_mem_size_prio,
                        "Taint-Size-Prio-Reversed-T":
                            taint_time_size_prio_rev,
                        "Taint-Size-Prio-Reversed-M":
                            taint_mem_size_prio_rev,
                        "Taint-Depth-Prio-T":
                            taint_time_depth_prio,
                        "Taint-Depth-Prio-M":
                            taint_mem_depth_prio,
                        "Taint-Depth-Prio-Reversed-T":
                            taint_time_depth_prio_rev,
                        "Taint-Depth-Prio-Reversed-M":
                            taint_mem_depth_prio_rev,
                        "LCA-Stack-T":
                            lca_time_stack,
                        "LCA-Stack-M":
                            lca_mem_stack,
                        "LCA-Queue-T":
                            lca_time_queue,
                        "LCA-Queue-M":
                            lca_mem_queue,
                        "LCA-Size-Prio-T":
                            lca_time_size_prio,
                        "LCA-Size-Prio-M":
                            lca_mem_size_prio,
                        "LCA-Size-Prio-Reversed-T":
                            lca_time_size_prio_rev,
                        "LCA-Size-Prio-Reversed-M":
                            lca_mem_size_prio_rev,
                        "LCA-Depth-Prio-T":
                            lca_time_depth_prio,
                        "LCA-Depth-Prio-M":
                            lca_mem_depth_prio,
                        "LCA-Depth-Prio-Reversed-T":
                            lca_time_depth_prio_rev,
                        "LCA-Depth-Prio-Reversed-M":
                            lca_mem_depth_prio_rev,
                    }
                }

                cs_data.append(pd.DataFrame.from_dict(cs_dict, orient="index"))

        if len(cs_data) == 0:
            raise TableDataEmpty()

        df = pd.concat(cs_data).sort_index()
        print(df)
        print(df.columns)

        df.columns = pd.MultiIndex.from_tuples([
            ('', '', 'Revision'),
            ('', '', 'Domain'),
            ('', '', 'LOC'),
            ('', '', 'IR-LOC'),
            ('Typestate', 'Stack', 'Time (s)'),
            ('Typestate', 'Stack', 'Mem (mbytes)'),
            ('Typestate', 'Queue', 'Time (s)'),
            ('Typestate', 'Queue', 'Mem (mbytes)'),
            ('Typestate', 'Size-Prio', 'Time (s)'),
            ('Typestate', 'Size-Prio', 'Mem (mbytes)'),
            ('Typestate', 'Size-Prio-Reversed', 'Time (s)'),
            ('Typestate', 'Size-Prio-Reversed', 'Mem (mbytes)'),
            ('Typestate', 'Depth-Prio', 'Time (s)'),
            ('Typestate', 'Depth-Prio', 'Mem (mbytes)'),
            ('Typestate', 'Depth-Prio-Reversed', 'Time (s)'),
            ('Typestate', 'Depth-Prio-Reversed', 'Mem (mbytes)'),
            ('Taint', 'Stack', 'Time (s)'),
            ('Taint', 'Stack', 'Mem (mbytes)'),
            ('Taint', 'Queue', 'Time (s)'),
            ('Taint', 'Queue', 'Mem (mbytes)'),
            ('Taint', 'Size-Prio', 'Time (s)'),
            ('Taint', 'Size-Prio', 'Mem (mbytes)'),
            ('Taint', 'Size-Prio-Reversed', 'Time (s)'),
            ('Taint', 'Size-Prio-Reversed', 'Mem (mbytes)'),
            ('Taint', 'Depth-Prio', 'Time (s)'),
            ('Taint', 'Depth-Prio', 'Mem (mbytes)'),
            ('Taint', 'Depth-Prio-Reversed', 'Time (s)'),
            ('Taint', 'Depth-Prio-Reversed', 'Mem (mbytes)'),
            ('LCA', 'Stack', 'Time (s)'),
            ('LCA', 'Stack', 'Mem (mbytes)'),
            ('LCA', 'Queue', 'Time (s)'),
            ('LCA', 'Queue', 'Mem (mbytes)'),
            ('LCA', 'Size-Prio', 'Time (s)'),
            ('LCA', 'Size-Prio', 'Mem (mbytes)'),
            ('LCA', 'Size-Prio-Reversed', 'Time (s)'),
            ('LCA', 'Size-Prio-Reversed', 'Mem (mbytes)'),
            ('LCA', 'Depth-Prio', 'Time (s)'),
            ('LCA', 'Depth-Prio', 'Mem (mbytes)'),
            ('LCA', 'Depth-Prio-Reversed', 'Time (s)'),
            ('LCA', 'Depth-Prio-Reversed', 'Mem (mbytes)'),
        ])

        print(df)

        cluster_memory_limit = 128000  # mbytes
        dev_memory_limit = 32000  # mbytes

        style: pd.io.formats.style.Styler = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            # style.highlight_between(
            #     left=cluster_memory_limit,
            #     props='cellcolor:{red};',
            #     subset=[('Typestate', 'Mem (mbytes)'),
            #             ('Taint', 'Mem (mbytes)'), ('Taint', 'Mem (mbytes)')]
            # )
            # style.highlight_between(
            #     left=dev_memory_limit,
            #     right=cluster_memory_limit,
            #     props='cellcolor:{orange};',
            #     subset=[('Typestate', 'Mem (mbytes)'),
            #             ('Taint', 'Mem (mbytes)'), ('Taint', 'Mem (mbytes)')]
            # )
            # df.style.format('j')
            kwargs["column_format"
                  ] = "lr|crr|rrrrrrrrrrrr|rrrrrrrrrrrr|rrrrrrrrrrrr"
            kwargs["multicol_align"] = "c|"
            # kwargs["multicolumn"] = True
            kwargs['position'] = 't'
            kwargs[
                "caption"
            ] = f"""On the left, we see all evaluted projectes with additional information, such as, revision we analyzed, the amount of C/C++ code.
The three columns on the right show time and memory consumption of the benchmarked analyses utilizing the current version of the IDE solver.
The orange cells indicate that the memory of a usual developer maschine ({dev_memory_limit} mbytes) was exceeded and the red cells indicate that even a compute cluster with {cluster_memory_limit} mbytes would be not enough."""
            style.format(precision=2)

        return dataframe_to_table(
            df,
            table_format,
            style,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class PhasarIterIDEStatsWL_LCA(
    Table, table_name="phasar-iter-ide-stats-wl-lca"
):

    def get_time_and_mem(self, report_entry):
        time = np.nan
        mem = np.nan
        if report_entry:
            time = np.mean(report_entry.measurements_wall_clock_time)
            mem = from_kbytes_to_mbytes(
                np.mean(report_entry.max_resident_sizes)
            )
        return (time, mem)

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        cs_data: tp.List[pd.DataFrame] = []

        for case_study in get_loaded_paper_config().get_all_case_studies():
            print(f"Working on {case_study.project_name}")
            project_name = case_study.project_name
            report_files = get_processed_revisions_files(
                case_study.project_name, IDELinearConstantAnalysisExperiment,
                PhasarIterIDEStatsReport,
                get_case_study_file_name_filter(case_study)
            )
            # print(f"{report_files=}")

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

                lca_time_stack, lca_mem_stack = self.get_time_and_mem(
                    report.new_lca_stack
                )
                lca_time_queue, lca_mem_queue = self.get_time_and_mem(
                    report.new_lca_queue
                )
                lca_time_size_prio, lca_mem_size_prio = self.get_time_and_mem(
                    report.new_lca_size_prio
                )
                lca_time_size_prio_rev, lca_mem_size_prio_rev = self.get_time_and_mem(
                    report.new_lca_size_prio_rev
                )
                lca_time_depth_prio, lca_mem_depth_prio = self.get_time_and_mem(
                    report.new_lca_depth_prio
                )
                lca_time_depth_prio_rev, lca_mem_depth_prio_rev = self.get_time_and_mem(
                    report.new_lca_depth_prio_rev
                )

                cs_dict = {
                    latex_sanitize_project_name(project_name): {
                        "Revision":
                            str(revision.short_hash),
                        "Domain":
                            str(project_cls.DOMAIN)[0].upper() +
                            str(project_cls.DOMAIN)[1:],
                        "LOC":
                            calc_repo_loc(project_repo, rev_range),
                        "IR-LOC":
                            report.basic_bc_stats.num_instructions,
                        "LCA-Stack-T":
                            lca_time_stack,
                        "LCA-Stack-M":
                            lca_mem_stack,
                        "LCA-Queue-T":
                            lca_time_queue,
                        "LCA-Queue-M":
                            lca_mem_queue,
                        "LCA-Size-Prio-T":
                            lca_time_size_prio,
                        "LCA-Size-Prio-M":
                            lca_mem_size_prio,
                        "LCA-Size-Prio-Reversed-T":
                            lca_time_size_prio_rev,
                        "LCA-Size-Prio-Reversed-M":
                            lca_mem_size_prio_rev,
                        "LCA-Depth-Prio-T":
                            lca_time_depth_prio,
                        "LCA-Depth-Prio-M":
                            lca_mem_depth_prio,
                        "LCA-Depth-Prio-Reversed-T":
                            lca_time_depth_prio_rev,
                        "LCA-Depth-Prio-Reversed-M":
                            lca_mem_depth_prio_rev,
                    }
                }

                cs_data.append(pd.DataFrame.from_dict(cs_dict, orient="index"))

        if len(cs_data) == 0:
            raise TableDataEmpty()

        df = pd.concat(cs_data).sort_index()
        print(df)
        print(df.columns)

        df.columns = pd.MultiIndex.from_tuples([
            ('', '', 'Revision'),
            ('', '', 'Domain'),
            ('', '', 'LOC'),
            ('', '', 'IR-LOC'),
            ('LCA', 'Stack', 'Time (s)'),
            ('LCA', 'Stack', 'Mem (mbytes)'),
            ('LCA', 'Queue', 'Time (s)'),
            ('LCA', 'Queue', 'Mem (mbytes)'),
            ('LCA', 'Size-Prio', 'Time (s)'),
            ('LCA', 'Size-Prio', 'Mem (mbytes)'),
            ('LCA', 'Size-Prio-Reversed', 'Time (s)'),
            ('LCA', 'Size-Prio-Reversed', 'Mem (mbytes)'),
            ('LCA', 'Depth-Prio', 'Time (s)'),
            ('LCA', 'Depth-Prio', 'Mem (mbytes)'),
            ('LCA', 'Depth-Prio-Reversed', 'Time (s)'),
            ('LCA', 'Depth-Prio-Reversed', 'Mem (mbytes)'),
        ])

        print(df)

        cluster_memory_limit = 128000  # mbytes
        dev_memory_limit = 32000  # mbytes

        style: pd.io.formats.style.Styler = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            # style.highlight_between(
            #     left=cluster_memory_limit,
            #     props='cellcolor:{red};',
            #     subset=[('Typestate', 'Mem (mbytes)'),
            #             ('Taint', 'Mem (mbytes)'), ('Taint', 'Mem (mbytes)')]
            # )
            # style.highlight_between(
            #     left=dev_memory_limit,
            #     right=cluster_memory_limit,
            #     props='cellcolor:{orange};',
            #     subset=[('Typestate', 'Mem (mbytes)'),
            #             ('Taint', 'Mem (mbytes)'), ('Taint', 'Mem (mbytes)')]
            # )
            # df.style.format('j')
            kwargs["column_format"] = "lr|crr|rrrrrrrrrrrr|"
            kwargs["multicol_align"] = "c|"
            # kwargs["multicolumn"] = True
            kwargs['position'] = 't'
            kwargs[
                "caption"
            ] = f"""On the left, we see all evaluted projectes with additional information, such as, revision we analyzed, the amount of C/C++ code.
The three columns on the right show time and memory consumption of the benchmarked analyses utilizing the current version of the IDE solver.
The orange cells indicate that the memory of a usual developer maschine ({dev_memory_limit} mbytes) was exceeded and the red cells indicate that even a compute cluster with {cluster_memory_limit} mbytes would be not enough."""
            style.format(precision=2)

        return dataframe_to_table(
            df,
            table_format,
            style,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class PhasarIterIDEStatsWL_Taint(
    Table, table_name="phasar-iter-ide-stats-wl-taint"
):

    def get_time_and_mem(self, report_entry):
        time = np.nan
        mem = np.nan
        if report_entry:
            time = np.mean(report_entry.measurements_wall_clock_time)
            mem = from_kbytes_to_mbytes(
                np.mean(report_entry.max_resident_sizes)
            )
        return (time, mem)

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        cs_data: tp.List[pd.DataFrame] = []

        for case_study in get_loaded_paper_config().get_all_case_studies():
            print(f"Working on {case_study.project_name}")
            project_name = case_study.project_name
            report_files = get_processed_revisions_files(
                case_study.project_name, IDELinearConstantAnalysisExperiment,
                PhasarIterIDEStatsReport,
                get_case_study_file_name_filter(case_study)
            )
            # print(f"{report_files=}")

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

                taint_time_stack, taint_mem_stack = self.get_time_and_mem(
                    report.new_taint_stack
                )
                taint_time_queue, taint_mem_queue = self.get_time_and_mem(
                    report.new_taint_queue
                )
                taint_time_size_prio, taint_mem_size_prio = self.get_time_and_mem(
                    report.new_taint_size_prio
                )
                taint_time_size_prio_rev, taint_mem_size_prio_rev = self.get_time_and_mem(
                    report.new_taint_size_prio_rev
                )
                taint_time_depth_prio, taint_mem_depth_prio = self.get_time_and_mem(
                    report.new_taint_depth_prio
                )
                taint_time_depth_prio_rev, taint_mem_depth_prio_rev = self.get_time_and_mem(
                    report.new_taint_depth_prio_rev
                )

                cs_dict = {
                    latex_sanitize_project_name(project_name): {
                        "Revision":
                            str(revision.short_hash),
                        "Domain":
                            str(project_cls.DOMAIN)[0].upper() +
                            str(project_cls.DOMAIN)[1:],
                        "LOC":
                            calc_repo_loc(project_repo, rev_range),
                        "IR-LOC":
                            report.basic_bc_stats.num_instructions,
                        "Taint-Stack-T":
                            taint_time_stack,
                        "Taint-Stack-M":
                            taint_mem_stack,
                        "Taint-Queue-T":
                            taint_time_queue,
                        "Taint-Queue-M":
                            taint_mem_queue,
                        "Taint-Size-Prio-T":
                            taint_time_size_prio,
                        "Taint-Size-Prio-M":
                            taint_mem_size_prio,
                        "Taint-Size-Prio-Reversed-T":
                            taint_time_size_prio_rev,
                        "Taint-Size-Prio-Reversed-M":
                            taint_mem_size_prio_rev,
                        "Taint-Depth-Prio-T":
                            taint_time_depth_prio,
                        "Taint-Depth-Prio-M":
                            taint_mem_depth_prio,
                        "Taint-Depth-Prio-Reversed-T":
                            taint_time_depth_prio_rev,
                        "Taint-Depth-Prio-Reversed-M":
                            taint_mem_depth_prio_rev,
                    }
                }

                cs_data.append(pd.DataFrame.from_dict(cs_dict, orient="index"))

        if len(cs_data) == 0:
            raise TableDataEmpty()

        df = pd.concat(cs_data).sort_index()
        print(df)
        print(df.columns)

        df.columns = pd.MultiIndex.from_tuples([
            ('', '', 'Revision'),
            ('', '', 'Domain'),
            ('', '', 'LOC'),
            ('', '', 'IR-LOC'),
            ('Taint', 'Stack', 'Time (s)'),
            ('Taint', 'Stack', 'Mem (mbytes)'),
            ('Taint', 'Queue', 'Time (s)'),
            ('Taint', 'Queue', 'Mem (mbytes)'),
            ('Taint', 'Size-Prio', 'Time (s)'),
            ('Taint', 'Size-Prio', 'Mem (mbytes)'),
            ('Taint', 'Size-Prio-Reversed', 'Time (s)'),
            ('Taint', 'Size-Prio-Reversed', 'Mem (mbytes)'),
            ('Taint', 'Depth-Prio', 'Time (s)'),
            ('Taint', 'Depth-Prio', 'Mem (mbytes)'),
            ('Taint', 'Depth-Prio-Reversed', 'Time (s)'),
            ('Taint', 'Depth-Prio-Reversed', 'Mem (mbytes)'),
        ])

        print(df)

        cluster_memory_limit = 128000  # mbytes
        dev_memory_limit = 32000  # mbytes

        style: pd.io.formats.style.Styler = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            # style.highlight_between(
            #     left=cluster_memory_limit,
            #     props='cellcolor:{red};',
            #     subset=[('Typestate', 'Mem (mbytes)'),
            #             ('Taint', 'Mem (mbytes)'), ('Taint', 'Mem (mbytes)')]
            # )
            # style.highlight_between(
            #     left=dev_memory_limit,
            #     right=cluster_memory_limit,
            #     props='cellcolor:{orange};',
            #     subset=[('Typestate', 'Mem (mbytes)'),
            #             ('Taint', 'Mem (mbytes)'), ('Taint', 'Mem (mbytes)')]
            # )
            # df.style.format('j')
            kwargs["column_format"] = "lr|crr|rrrrrrrrrrrr|"
            kwargs["multicol_align"] = "c|"
            # kwargs["multicolumn"] = True
            kwargs['position'] = 't'
            kwargs[
                "caption"
            ] = f"""On the left, we see all evaluted projectes with additional information, such as, revision we analyzed, the amount of C/C++ code.
The three columns on the right show time and memory consumption of the benchmarked analyses utilizing the current version of the IDE solver.
The orange cells indicate that the memory of a usual developer maschine ({dev_memory_limit} mbytes) was exceeded and the red cells indicate that even a compute cluster with {cluster_memory_limit} mbytes would be not enough."""
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
        lca = PhasarIterIDEStatsWL_LCA(self.table_config, **self.table_kwargs)
        taint = PhasarIterIDEStatsWL_Taint(
            self.table_config, **self.table_kwargs
        )
        return [
            PhasarIterIDEStats(self.table_config, **self.table_kwargs), lca,
            taint
        ]


class PhasarIterIDEOldVSNew(Table, table_name="phasar-iter-ide-old-new"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        cs_data: tp.List[pd.DataFrame] = []

        for case_study in get_loaded_paper_config().get_all_case_studies():
            print(f"Working on {case_study.project_name}")
            project_name = latex_sanitize_project_name(case_study.project_name)
            report_files = get_processed_revisions_files(
                case_study.project_name, IDELinearConstantAnalysisExperiment,
                PhasarIterIDEStatsReport,
                get_case_study_file_name_filter(case_study)
            )

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
            kwargs["column_format"] = "l|c|rrrr|rrrr|c|rrrr|rrrr|c|rrrr|rrrr|"
            kwargs["multicol_align"] = "c|"
            # kwargs["multicolumn"] = True
            kwargs['position'] = 't'
            kwargs[
                "caption"
            ] = """Results of our overall comparision between the old IDESolver with our newly updated iterative IDESolver. We report the mean runtime of both versions, as well as, the mean speedup $\mathcal{S}$ and it's standard deviation $s$.
$\mathcal{S}$ was computed as the mean over all speedups in the cartesian product of all old and new measurements.
"""
            style.format(precision=2)

        def add_extras(doc: Document) -> None:
            doc.packages.append(Package("amssymb"))
            doc.append(NoEscape("\setlength{\\tabcolsep}{4pt}"))

        return dataframe_to_table(
            df,
            table_format,
            style,
            wrap_table=wrap_table,
            wrap_landscape=True,
            margin=0.0,
            document_decorator=add_extras,
            **kwargs
        )

    def compute_typestate_stats(self, report: PhasarIterIDEStatsReport):
        stats = dict()
        stats[("Typestate", "", "C")] = get_compare_mark(report.cmp_typestate)
        stats.update(
            self.__compute_delta_comp(
                "Typestate", report.old_typestate, report.new_typestate
            )
        )

        return stats

    def compute_taint(self, report: PhasarIterIDEStatsReport):
        stats = dict()
        stats[("Taint", "", "C")] = get_compare_mark(report.cmp_taint)
        stats.update(
            self.__compute_delta_comp(
                "Taint", report.old_taint, report.new_taint
            )
        )

        return stats

    def compute_lca_stats(self, report: PhasarIterIDEStatsReport):
        stats = dict()
        stats[("LCA", "", "C")] = get_compare_mark(report.cmp_lca)
        stats.update(
            self.__compute_delta_comp("LCA", report.old_lca, report.new_lca)
        )

        return stats

    @staticmethod
    def __compute_speedups(
        old_measurements: tp.List[float], new_measurements: tp.List[float]
    ) -> tp.List[float]:
        return list(
            map(
                lambda x: round(x[0] / x[1], 3),
                itertools.product(old_measurements, new_measurements)
            )
        )

    def __compute_delta_comp(
        self, name: str, old_time_report: tp.Optional[TimeReportAggregate],
        new_time_report: tp.Optional[TimeReportAggregate]
    ):
        time_old = np.nan
        time_new = np.nan
        time_speedup = np.nan
        time_stddev = np.nan

        memory_old = np.nan
        memory_new = np.nan
        memory_speedup = np.nan
        memory_stddev = np.nan

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

        if old_time_report and new_time_report:
            time_speedups = PhasarIterIDEOldVSNew.__compute_speedups(
                old_time_report.measurements_wall_clock_time,
                new_time_report.measurements_wall_clock_time
            )
            memory_speedups = PhasarIterIDEOldVSNew.__compute_speedups(
                all_from_kbytes_to_mbytes(old_time_report.max_resident_sizes),
                all_from_kbytes_to_mbytes(new_time_report.max_resident_sizes)
            )

            time_speedup = np.mean(time_speedups)
            memory_speedup = np.mean(memory_speedups)

            time_stddev = np.std(time_speedups)
            memory_stddev = np.std(memory_speedups)

        return {(name, 'Time', 'Old'): time_old,
                (name, 'Time', 'New'): time_new,
                (name, 'Time', '$\mathcal{S}$'): time_speedup,
                (name, 'Time', '$s$'): time_stddev,
                (name, 'Memory', 'Old'): memory_old,
                (name, 'Memory', 'New'): memory_new,
                (name, 'Memory', '$\mathcal{S}$'): memory_speedup,
                (name, 'Memory', '$s$'): memory_stddev}


class PhasarIterIDEOldVSNewGenerator(
    TableGenerator, generator_name="phasar-iter-ide-old-new", options=[]
):
    """TODO: """

    def generate(self) -> tp.List[Table]:
        return [PhasarIterIDEOldVSNew(self.table_config, **self.table_kwargs)]


class PhasarIterIDEJF1vsJF2(Table, table_name="phasar-iter-ide-jf1-jf2"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        cs_data: tp.List[pd.DataFrame] = []

        for case_study in get_loaded_paper_config().get_all_case_studies():
            print(f"Working on {case_study.project_name}")
            project_name = latex_sanitize_project_name(case_study.project_name)
            report_files = get_processed_revisions_files(
                case_study.project_name, IDELinearConstantAnalysisExperiment,
                PhasarIterIDEStatsReport,
                get_case_study_file_name_filter(case_study)
            )

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
            kwargs["column_format"] = "l|rrrr|rrrr|rrrr|rrrr|rrrr|rrrr|"
            kwargs["multicol_align"] = "c|"
            # kwargs["multicolumn"] = True
            kwargs['position'] = 't'
            kwargs[
                "caption"
            ] = """Results of our overall comparision between the two jump-function representations within our newly updated iterative IDESolver. We report the mean runtime of both versions, as well as, the mean speedup $\mathcal{S}$ and it's standard deviation $s$.
$\mathcal{S}$ was computed as the mean over all speedups in the cartesian product of all measurements.
"""
            style.format(precision=2)

        def add_extras(doc: Document) -> None:
            doc.packages.append(Package("amssymb"))
            doc.append(NoEscape("\setlength{\\tabcolsep}{4pt}"))

        return dataframe_to_table(
            df,
            table_format,
            style,
            wrap_table=wrap_table,
            wrap_landscape=True,
            margin=0.0,
            document_decorator=add_extras,
            **kwargs
        )

    def compute_typestate_stats(self, report: PhasarIterIDEStatsReport):
        stats = dict()
        stats.update(
            self.__compute_delta_comp(
                "Typestate", report.new_typestate_jf1, report.new_typestate
            )
        )

        return stats

    def compute_taint(self, report: PhasarIterIDEStatsReport):
        stats = dict()
        stats.update(
            self.__compute_delta_comp(
                "Taint", report.new_taint_jf1, report.new_taint
            )
        )

        return stats

    def compute_lca_stats(self, report: PhasarIterIDEStatsReport):
        stats = dict()
        stats.update(
            self.__compute_delta_comp(
                "LCA", report.new_lca_jf1, report.new_lca
            )
        )

        return stats

    @staticmethod
    def __compute_speedups(
        old_measurements: tp.List[float], new_measurements: tp.List[float]
    ) -> tp.List[float]:
        return list(
            map(
                lambda x: round(x[0] / x[1], 3),
                itertools.product(old_measurements, new_measurements)
            )
        )

    def __compute_delta_comp(
        self, name: str, old_time_report: tp.Optional[TimeReportAggregate],
        new_time_report: tp.Optional[TimeReportAggregate]
    ):
        time_old = np.nan
        time_new = np.nan
        time_speedup = np.nan
        time_stddev = np.nan

        memory_old = np.nan
        memory_new = np.nan
        memory_speedup = np.nan
        memory_stddev = np.nan

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

        if old_time_report and new_time_report:
            time_speedups = PhasarIterIDEJF1vsJF2.__compute_speedups(
                old_time_report.measurements_wall_clock_time,
                new_time_report.measurements_wall_clock_time
            )
            memory_speedups = PhasarIterIDEJF1vsJF2.__compute_speedups(
                all_from_kbytes_to_mbytes(old_time_report.max_resident_sizes),
                all_from_kbytes_to_mbytes(new_time_report.max_resident_sizes)
            )

            time_speedup = np.mean(time_speedups)
            memory_speedup = np.mean(memory_speedups)

            time_stddev = np.std(time_speedups)
            memory_stddev = np.std(memory_speedups)

        return {(name, 'Time', 'JF1'): time_old,
                (name, 'Time', 'JF2'): time_new,
                (name, 'Time', '$\mathcal{S}$'): time_speedup,
                (name, 'Time', '$s$'): time_stddev,
                (name, 'Memory', 'JF1'): memory_old,
                (name, 'Memory', 'JF2'): memory_new,
                (name, 'Memory', '$\mathcal{S}$'): memory_speedup,
                (name, 'Memory', '$s$'): memory_stddev}


class PhasarIterIDEJF1vsJF2Generator(
    TableGenerator, generator_name="phasar-iter-ide-old-new", options=[]
):
    """TODO: """

    def generate(self) -> tp.List[Table]:
        return [PhasarIterIDEJF1vsJF2(self.table_config, **self.table_kwargs)]
