"""Module for the PerfInterDataTable."""
import typing as tp
from enum import Enum
from glob import glob
from pathlib import Path

import pandas as pd

from varats.experiments.base.perf_sampling import (
    PerfSampling,
    PerfSamplingSynth,
)
from varats.jupyterhelper.file import (
    load_wl_function_overhead_report_aggregate,
    load_wl_time_report_aggregate,
    load_mpr_wl_function_overhead_report_aggregate,
    load_mpr_wl_time_report_aggregate,
)
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.project.project_util import get_project_cls_by_name
from varats.project.varats_project import VProject
from varats.provider.patch.patch_provider import PatchProvider
from varats.report.function_overhead_report import (
    WLFunctionOverheadReportAggregate,
    MPRWLFunctionOverheadReportAggregate,
)
from varats.report.gnu_time_report import (
    WLTimeReportAggregate,
    MPRWLTimeReportAggregate,
)
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY
from varats.utils.settings import bb_cfg

if tp.TYPE_CHECKING:
    from varats.paper_mgmt.case_study import CaseStudy


class ReportStatus(Enum):
    """Enum to represent the status of a report."""
    OK = '\u2713'
    MISSING = '\u2717'
    BROKEN = '!'


def _is_ok_twl_report(
    report: tp.Optional[WLTimeReportAggregate], reps: int = 10
) -> ReportStatus:
    if report is None:
        return ReportStatus.MISSING

    wl = next(iter(report.workload_names()))
    times = report.measurements_wall_clock_time(wl)

    if len(times) == reps and all([t > 0.0 for t in times]):
        return ReportStatus.OK
    else:
        return ReportStatus.BROKEN


def _is_ok_foh_report(
    report: tp.Optional[WLFunctionOverheadReportAggregate],
    reps: int = 10,
    threshold: int = 5
) -> ReportStatus:
    if report is None:
        return ReportStatus.MISSING
    wl = next(iter(report.workload_names()))
    reports = report.reports(wl)

    if len(reports) == reps and all([
        len(r.hot_functions(threshold)) > 0 for r in reports
    ]):
        return ReportStatus.OK
    else:
        return ReportStatus.BROKEN


class PerfInterDataTable(Table, table_name="performance_interaction_data"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        entries: tp.List[tp.Dict[str, tp.Any]] = []

        for case_study in case_studies:
            project_name = case_study.project_name

            foh_report_files = get_processed_revisions_files(
                project_name,
                PerfSampling,
                WLFunctionOverheadReportAggregate,
                get_case_study_file_name_filter(case_study),
                only_newest=False
            )

            twl_report_files = get_processed_revisions_files(
                project_name,
                PerfSampling,
                WLTimeReportAggregate,
                get_case_study_file_name_filter(case_study),
                only_newest=False
            )

            if not foh_report_files or not twl_report_files:
                continue

            foh_report_file_data = pd.DataFrame.from_records([{
                "revision": report_file.report_filename.commit_hash,
                "config_id": report_file.report_filename.config_id,
                "report_file": report_file
            } for report_file in foh_report_files])

            twl_report_file_data = pd.DataFrame.from_records([{
                "revision": report_file.report_filename.commit_hash,
                "config_id": report_file.report_filename.config_id,
                "report_file": report_file
            } for report_file in twl_report_files])

            for revision in case_study.revisions:
                short_revision = revision.to_short_commit_hash()
                fho_missing_files = []
                fho_broken_reports = []
                twl_missing_files = []
                twl_broken_reports = []

                for config_id in case_study.get_config_ids_for_revision(
                    revision
                ):
                    if (
                        foh_report_file := foh_report_file_data[(
                            foh_report_file_data["revision"] == short_revision
                        ) & (foh_report_file_data["config_id"] == config_id)]
                    ).empty:
                        fho_missing_files.append((revision, config_id))
                        print(
                            f"[{project_name}] Missing FOH report for {short_revision} and config {config_id}"
                        )
                    else:
                        foh_report = load_wl_function_overhead_report_aggregate(
                            foh_report_file["report_file"].iat[0]
                        )
                        if _is_ok_foh_report(foh_report) != ReportStatus.OK:
                            fho_broken_reports.append((revision, config_id))
                            print(
                                f"[{project_name}] Broken FOH report for {short_revision} and config {config_id}"
                            )

                    if (
                        twl_report_file := twl_report_file_data[(
                            twl_report_file_data["revision"] == short_revision
                        ) & (twl_report_file_data["config_id"] == config_id)]
                    ).empty:
                        twl_missing_files.append((revision, config_id))
                        print(
                            f"[{project_name}] Missing TWL report for {short_revision} and config {config_id}"
                        )
                    else:
                        twl_report = load_wl_time_report_aggregate(
                            twl_report_file["report_file"].iat[0]
                        )
                        if _is_ok_twl_report(twl_report) != ReportStatus.OK:
                            twl_broken_reports.append((revision, config_id))
                            print(
                                f"[{project_name}] Broken TWL report for {short_revision} and config {config_id}"
                            )

                broken_revs = set(
                    fho_missing_files + fho_broken_reports + twl_missing_files +
                    twl_broken_reports
                )
                with open(f"broken_revs_{project_name}.txt", "a") as f:
                    result_folder = \
                        Path(str(bb_cfg()["varats"]["outfile"])) / project_name
                    project_cls: tp.Type[VProject] = get_project_cls_by_name(
                        project_name
                    )

                    for rev, config in broken_revs:
                        binary_name = project_cls.binaries_for_revision(
                            rev.to_short_commit_hash()
                        )[0].name
                        perf_reports = glob(
                            str(
                                result_folder /
                                f"PS-WLFORAgg-{project_name}-{binary_name}-{rev.short_hash}"
                                / f"*config-{config}_success.zip"
                            )
                        )
                        time_reports = glob(
                            str(
                                result_folder /
                                f"PS-WLTRAgg-{project_name}-{binary_name}-{rev.short_hash}"
                                / f"*config-{config}_success.zip"
                            )
                        )
                        for perf_report in perf_reports:
                            f.write(perf_report + "\n")
                        for time_report in time_reports:
                            f.write(time_report + "\n")

                entries.append({
                    "Project":
                        project_name,
                    "Revision":
                        short_revision.hash,
                    "Configs":
                        len(case_study.get_config_ids_for_revision(revision)),
                    "FHO Missing":
                        len(fho_missing_files),
                    "FHO Broken":
                        len(fho_broken_reports),
                    "TWL Missing":
                        len(twl_missing_files),
                    "TWL Broken":
                        len(twl_broken_reports)
                })

        df = pd.DataFrame.from_records(entries).drop_duplicates()
        df.sort_values(["Project", "Revision"], inplace=True)
        df.set_index(
            ["Project", "Revision"],
            inplace=True,
        )

        kwargs: tp.Dict[str, tp.Any] = {}

        return dataframe_to_table(
            df,
            table_format,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class PerfInterDataTableGenerator(
    TableGenerator, generator_name="perf-inter-data", options=[]
):
    """Generator for `PerfInterDataTable`."""

    def generate(self) -> tp.List[Table]:
        return [PerfInterDataTable(self.table_config, **self.table_kwargs)]


class PerfInterSynthDataTable(
    Table, table_name="performance_interaction_synth_data"
):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_study: CaseStudy = self.table_kwargs["case_study"]
        project_name = case_study.project_name
        project_cls = get_project_cls_by_name(project_name)
        patch_provider = PatchProvider.get_provider_for_project(project_cls)

        foh_report_files = get_processed_revisions_files(
            project_name,
            PerfSamplingSynth,
            MPRWLFunctionOverheadReportAggregate,
            get_case_study_file_name_filter(case_study),
            only_newest=False
        )

        twl_report_files = get_processed_revisions_files(
            project_name,
            PerfSamplingSynth,
            MPRWLTimeReportAggregate,
            get_case_study_file_name_filter(case_study),
            only_newest=False
        )

        entries = {}

        foh_report_file_data = pd.DataFrame.from_records([{
            "revision": report_file.report_filename.commit_hash,
            "config_id": report_file.report_filename.config_id,
            "report_file": report_file
        } for report_file in foh_report_files])

        twl_report_file_data = pd.DataFrame.from_records([{
            "revision": report_file.report_filename.commit_hash,
            "config_id": report_file.report_filename.config_id,
            "report_file": report_file
        } for report_file in twl_report_files])

        for revision in case_study.revisions:
            short_revision = revision.to_short_commit_hash()
            patches = patch_provider.get_patches_for_revision(short_revision)
            change_patches = patches.all_of("perf_inter", "change")

            for config_id in case_study.get_config_ids_for_revision(revision):
                patch_data = dict()

                if (
                    foh_report_file := foh_report_file_data[
                        (foh_report_file_data["revision"] == short_revision) &
                        (foh_report_file_data["config_id"] == config_id)]
                ).empty:
                    patch_data[("foh", "base")] = ReportStatus.MISSING
                    patch_data |= {
                        ("foh", patch.shortname): ReportStatus.MISSING
                        for patch in change_patches
                    }
                else:
                    foh_report = load_mpr_wl_function_overhead_report_aggregate(
                        foh_report_file["report_file"].iat[0]
                    )
                    patch_data[("foh", "base")] = _is_ok_foh_report(
                        foh_report.get_baseline_report()
                    )

                    for patch in change_patches:
                        patch_data[("foh", patch.shortname)
                                  ] = _is_ok_foh_report(
                                      foh_report.get_report_for_patch(
                                          patch.shortname
                                      )
                                  )

                if (
                    twl_report_file := twl_report_file_data[
                        (twl_report_file_data["revision"] == short_revision) &
                        (twl_report_file_data["config_id"] == config_id)]
                ).empty:
                    patch_data[("twl", "base")] = ReportStatus.MISSING
                    patch_data |= {
                        ("twl", patch.shortname): ReportStatus.MISSING
                        for patch in change_patches
                    }
                else:
                    twl_report = load_mpr_wl_time_report_aggregate(
                        twl_report_file["report_file"].iat[0]
                    )
                    patch_data[("twl", "base")] = _is_ok_twl_report(
                        twl_report.get_baseline_report()
                    )

                    for patch in change_patches:
                        patch_data[("twl", patch.shortname)
                                  ] = _is_ok_twl_report(
                                      twl_report.get_report_for_patch(
                                          patch.shortname
                                      )
                                  )

                entries |= {(short_revision.hash, config_id): patch_data}

        df = pd.DataFrame.from_dict(entries, orient='index')
        df.index = pd.MultiIndex.from_tuples(
            df.index, names=["Revision", "Config"]
        )
        df.columns = pd.MultiIndex.from_tuples(
            df.columns, names=["Report Type", "Patch"]
        )
        df.sort_index(axis='index', inplace=True)
        df.sort_index(axis='columns', inplace=True)
        df = df.map(lambda x: x.value if isinstance(x, ReportStatus) else x)

        kwargs: tp.Dict[str, tp.Any] = {}

        return dataframe_to_table(
            df,
            table_format,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class PerfInterSynthDataTableGenerator(
    TableGenerator,
    generator_name="perf-inter-synth-data",
    options=[REQUIRE_MULTI_CASE_STUDY]
):
    """Generator for `PerfInterSynthDataTable`."""

    def generate(self) -> tp.List[Table]:
        case_studies: tp.List[CaseStudy] = self.table_kwargs.pop("case_study")
        return [
            PerfInterSynthDataTable(
                self.table_config, case_study=cs, **self.table_kwargs
            ) for cs in case_studies
        ]
