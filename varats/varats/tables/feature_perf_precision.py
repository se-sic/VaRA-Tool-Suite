"""Module for the FeaturePerfPrecision tables."""
import re
import typing as tp
from pathlib import Path

import numpy as np
import pandas as pd
from plumbum import local, TF, RETCODE
from pylatex import Document, Package

from varats.data.databases.feature_perf_precision_database import (
    get_patch_names,
    get_regressing_config_ids_gt,
    map_to_positive_config_ids,
    map_to_negative_config_ids,
    Profiler,
    VXray,
    PIMTracer,
    EbpfTraceTEF,
    Baseline,
    compute_profiler_predictions,
    OverheadData,
    load_precision_data,
)
from varats.data.metrics import ConfusionMatrix
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import get_local_project_git_path
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.utils.git_util import calc_repo_loc, ChurnConfig, git


class FeaturePerfPrecisionTable(Table, table_name="fperf_precision"):
    """Table that compares the precision of different feature performance
    measurement approaches."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()
        profilers: tp.List[Profiler] = [VXray(), PIMTracer()]

        # Data aggregation
        df = pd.DataFrame()
        table_rows = []

        for case_study in case_studies:
            for patch_name in get_patch_names(case_study):
                rev = case_study.revisions[0]
                project_name = case_study.project_name

                ground_truth = get_regressing_config_ids_gt(
                    project_name, case_study, rev, patch_name
                )

                new_row = {
                    'CaseStudy':
                        project_name,
                    'Patch':
                        patch_name,
                    'Configs':
                        len(case_study.get_config_ids_for_revision(rev)),
                    'RegressedConfigs':
                        len(map_to_positive_config_ids(ground_truth))
                        if ground_truth else -1
                }

                for profiler in profilers:
                    # TODO: multiple patch cycles
                    predicted = compute_profiler_predictions(
                        profiler, project_name, case_study,
                        case_study.get_config_ids_for_revision(rev), patch_name
                    )

                    if ground_truth and predicted:
                        results = ConfusionMatrix(
                            map_to_positive_config_ids(ground_truth),
                            map_to_negative_config_ids(ground_truth),
                            map_to_positive_config_ids(predicted),
                            map_to_negative_config_ids(predicted)
                        )
                        new_row[f"{profiler.name}_precision"
                               ] = results.precision()
                        new_row[f"{profiler.name}_recall"] = results.recall()
                        new_row[f"{profiler.name}_baccuracy"
                               ] = results.balanced_accuracy()
                    else:
                        new_row[f"{profiler.name}_precision"] = np.nan
                        new_row[f"{profiler.name}_recall"] = np.nan
                        new_row[f"{profiler.name}_baccuracy"] = np.nan

                table_rows.append(new_row)
                # df.append(new_row, ignore_index=True)

        df = pd.concat([df, pd.DataFrame(table_rows)])
        df.sort_values(["CaseStudy"], inplace=True)
        print(f"{df=}")

        # insert totals
        totals = {
            'CaseStudy': "Total (avg)",
            "Configs": 0,
            "RegressedConfigs": 0
        }
        for profiler in profilers:
            totals[f"{profiler.name}_precision"] = df[
                f"{profiler.name}_precision"].mean()
            totals[f"{profiler.name}_recall"] = df[f"{profiler.name}_recall"
                                                  ].mean()
            totals[f"{profiler.name}_baccuracy"] = df[
                f"{profiler.name}_baccuracy"].mean()

        tdf = pd.DataFrame(totals, index=[0])
        df = pd.concat([df, tdf], ignore_index=True)

        print(f"{df=}")

        symb_precision = "\\textsc{PPV}"
        symb_recall = "\\textsc{TPR}"
        symb_b_accuracy = "\\textsc{BA}"
        symb_configs = "$\\mathbb{C}$"
        symb_regressed_configs = "$\\mathbb{R}$"

        print(f"{df=}")
        colum_setup = [(' ', 'CaseStudy'), (' ', 'Patch'),
                       ('', f'{symb_configs}'),
                       ('', f'{symb_regressed_configs}')]
        for profiler in profilers:
            colum_setup.append((profiler.name, f'{symb_precision}'))
            colum_setup.append((profiler.name, f'{symb_recall}'))
            colum_setup.append((profiler.name, f'{symb_b_accuracy}'))

        print(f"{colum_setup=}")
        df.columns = pd.MultiIndex.from_tuples(colum_setup)

        # Table config

        print(f"{df=}")

        style: pd.io.formats.style.Styler = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["hrules"] = True
            column_format = "l|rr"
            for _ in profilers:
                column_format += "|rrr"
            kwargs["column_format"] = column_format
            kwargs["multicol_align"] = "|c"
            kwargs[
                "caption"
            ] = f"""Localization precision of different performance profiling approaches to detect configuration-specific performance regression detection.
On the left, we show the amount of different configurations ({symb_configs}) analyzed and the amount of regressed configurations ({symb_regressed_configs}), determined through our baseline measurements.
Furthermore, the table depicts for each profiler, precision ({symb_precision}), recall ({symb_recall}), and balanced accuracy ({symb_b_accuracy}).
"""
            style.format(precision=2)
            style.hide()

        def add_extras(doc: Document) -> None:
            doc.packages.append(Package("amsmath"))
            doc.packages.append(Package("amssymb"))

        return dataframe_to_table(
            df,
            table_format,
            style=style,
            wrap_table=wrap_table,
            wrap_landscape=True,
            document_decorator=add_extras,
            **kwargs
        )


class FeaturePerfPrecisionTableGenerator(
    TableGenerator, generator_name="fperf-precision", options=[]
):
    """Generator for `FeaturePerfPrecisionTable`."""

    def generate(self) -> tp.List[Table]:
        return [
            FeaturePerfPrecisionTable(self.table_config, **self.table_kwargs)
        ]


class FeaturePerfOverheadTable(Table, table_name="fperf_overhead"):
    """Table that compares overhead of different feature performance measurement
    approaches."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()
        profilers: tp.List[Profiler] = [VXray(), PIMTracer()]

        # Data aggregation
        df = pd.DataFrame()
        table_rows = []

        for case_study in case_studies:
            rev = case_study.revisions[0]
            project_name = case_study.project_name

            overhead_ground_truth = OverheadData.compute_overhead_data(
                Baseline(), case_study, rev
            )
            if not overhead_ground_truth:
                print(
                    f"No baseline data for {case_study.project_name}, skipping"
                )
                continue

            new_row = {
                'CaseStudy': project_name,
                'WithoutProfiler_mean_time': overhead_ground_truth.mean_time(),
                'WithoutProfiler_mean_ctx': overhead_ground_truth.mean_ctx()
            }

            for profiler in profilers:
                profiler_overhead = OverheadData.compute_overhead_data(
                    profiler, case_study, rev
                )
                if profiler_overhead:
                    time_diff = profiler_overhead.config_wise_time_diff(
                        overhead_ground_truth
                    )
                    ctx_diff = profiler_overhead.config_wise_ctx_diff(
                        overhead_ground_truth
                    )
                    print(f"{time_diff=}")
                    new_row[f"{profiler.name}_time_mean"] = np.mean(
                        list(time_diff.values())
                    )
                    new_row[f"{profiler.name}_time_std"] = np.std(
                        list(time_diff.values())
                    )
                    new_row[f"{profiler.name}_time_max"] = np.max(
                        list(time_diff.values())
                    )
                    new_row[f"{profiler.name}_ctx_mean"] = np.mean(
                        list(ctx_diff.values())
                    )
                    new_row[f"{profiler.name}_ctx_std"] = np.std(
                        list(ctx_diff.values())
                    )
                    new_row[f"{profiler.name}_ctx_max"] = np.max(
                        list(ctx_diff.values())
                    )
                else:
                    new_row[f"{profiler.name}_time_mean"] = np.nan
                    new_row[f"{profiler.name}_time_std"] = np.nan
                    new_row[f"{profiler.name}_time_max"] = np.nan

                    new_row[f"{profiler.name}_ctx_mean"] = np.nan
                    new_row[f"{profiler.name}_ctx_std"] = np.nan
                    new_row[f"{profiler.name}_ctx_max"] = np.nan

            table_rows.append(new_row)
            # df.append(new_row, ignore_index=True)

        df = pd.concat([df, pd.DataFrame(table_rows)])
        df.sort_values(["CaseStudy"], inplace=True)
        print(f"{df=}")

        colum_setup = [('', '', 'CaseStudy'), ('Baseline', 'time', 'mean'),
                       ('Baseline', 'ctx', 'mean')]
        for profiler in profilers:
            colum_setup.append((profiler.name, 'time', 'mean'))
            colum_setup.append((profiler.name, 'time', 'std'))
            colum_setup.append((profiler.name, 'time', 'max'))

            colum_setup.append((profiler.name, 'ctx', 'mean'))
            colum_setup.append((profiler.name, 'ctx', 'std'))
            colum_setup.append((profiler.name, 'ctx', 'max'))

        print(f"{colum_setup=}")
        df.columns = pd.MultiIndex.from_tuples(colum_setup)

        # Table config

        print(f"{df=}")

        style: pd.io.formats.style.Styler = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["hrules"] = True
            column_format = "l|rr"
            for _ in profilers:
                column_format += "|rrrrrr"
            kwargs["column_format"] = column_format
            kwargs["multicol_align"] = "|c"
            kwargs["caption"
                  ] = """This table depicts the overhead measurement data.
For each case study, we show on the left the mean time it took to execute it without instrumentation (Baseline).
To the right of the baseline, we show for each profiler the induced overhead.
"""
            style.format(precision=2)
            style.hide()

        def add_extras(doc: Document) -> None:
            doc.packages.append(Package("amsmath"))
            doc.packages.append(Package("amssymb"))

        return dataframe_to_table(
            df,
            table_format,
            style=style,
            wrap_table=wrap_table,
            wrap_landscape=True,
            document_decorator=add_extras,
            **kwargs
        )


class FeaturePerfOverheadTableGenerator(
    TableGenerator, generator_name="fperf-overhead", options=[]
):
    """Generator for `FeaturePerfOverheadTable`."""

    def generate(self) -> tp.List[Table]:
        return [
            FeaturePerfOverheadTable(self.table_config, **self.table_kwargs)
        ]


class FeaturePerfMetricsOverviewTable(Table, table_name="fperf_overview"):
    """Table showing some general information about feature performance case
    studies."""

    # TODO: refactor out
    @staticmethod
    def _calc_folder_locs(repo_path: Path, rev_range: str, folder: str) -> int:
        churn_config = ChurnConfig.create_c_style_languages_config()
        file_pattern = re.compile(
            "|".join(churn_config.get_extensions_repr(r"^.*\.", r"$"))
        )

        loc: int = 0
        with local.cwd(repo_path):
            files = git(
                "ls-tree",
                "-r",
                "--name-only",
                rev_range,
            ).splitlines()

            for file in files:
                if not file.startswith(folder):
                    continue
                if file_pattern.match(file):
                    lines = git("show", f"{rev_range}:{file}").splitlines()
                    loc += len([line for line in lines if line])

        return loc

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()
        profilers: tp.List[Profiler] = [VXray(), PIMTracer(), EbpfTraceTEF()]

        df_precision = load_precision_data(case_studies, profilers)

        cs_data: tp.List[pd.DataFrame] = []
        for case_study in case_studies:
            project_name = case_study.project_name
            rev = case_study.revisions[0]
            project_git_path = get_local_project_git_path(project_name)

            cs_precision_data = df_precision[df_precision['CaseStudy'] ==
                                             project_name]
            regressions = len(cs_precision_data['Patch'].unique())

            locs: int
            if case_study.project_cls.DOMAIN == ProjectDomains.TEST:
                src_folder = f'projects/{project_name}'
                locs = self._calc_folder_locs(
                    project_git_path, rev.hash, src_folder
                )
            else:
                locs = calc_repo_loc(project_git_path, rev.hash)

            cs_dict = {
                project_name: {
                    "NumConfig":
                        len(case_study.get_config_ids_for_revision(rev)),
                    "Locs":
                        locs,
                    "Regressions":
                        regressions,
                }
            }

            cs_data.append(pd.DataFrame.from_dict(cs_dict, orient='index'))

        df = pd.concat(cs_data).sort_index()

        style = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["hrules"] = True
            style.format(thousands=r"\,")
        return dataframe_to_table(df, table_format, style, wrap_table, **kwargs)


class FeaturePerfMetricsOverviewTableGenerator(
    TableGenerator, generator_name="fperf-overview", options=[]
):
    """Generates a cs-metrics table for the selected case study(ies)."""

    def generate(self) -> tp.List[Table]:
        return [
            FeaturePerfMetricsOverviewTable(
                self.table_config, **self.table_kwargs
            )
        ]
