"""Module for the FeaturePerfPrecision tables."""
import re
import typing as tp
from pathlib import Path

import matplotlib.colors as colors
import matplotlib.pyplot as plt
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
    load_overhead_data,
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


def cmap_map(function, cmap):
    """
    Applies function (which should operate on vectors of shape 3: [r, g, b]), on
    colormap cmap.

    This routine will break any discontinuous points in a colormap.
    """
    cdict = cmap._segmentdata
    step_dict = {}
    # Firt get the list of points where the segments start or end
    for key in ('red', 'green', 'blue'):
        step_dict[key] = list(map(lambda x: x[0], cdict[key]))
    step_list = sum(step_dict.values(), [])
    step_list = np.array(list(set(step_list)))
    # Then compute the LUT, and apply the function to the LUT
    reduced_cmap = lambda step: np.array(cmap(step)[0:3])
    old_LUT = np.array(list(map(reduced_cmap, step_list)))
    new_LUT = np.array(list(map(function, old_LUT)))
    # Now try to make a minimal segment definition of the new LUT
    cdict = {}
    for i, key in enumerate(['red', 'green', 'blue']):
        this_cdict = {}
        for j, step in enumerate(step_list):
            if step in step_dict[key]:
                this_cdict[step] = new_LUT[j, i]
            elif new_LUT[j, i] != old_LUT[j, i]:
                this_cdict[step] = new_LUT[j, i]
        colorvector = list(map(lambda x: x + (x[1],), this_cdict.items()))
        colorvector.sort()
        cdict[key] = colorvector

    import matplotlib
    return matplotlib.colors.LinearSegmentedColormap('colormap', cdict, 1024)


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


def truncate_colormap(cmap, minval=0.0, maxval=1.0, n=100):
    new_cmap = colors.LinearSegmentedColormap.from_list(
        'trunc({n},{a:.2f},{b:.2f})'.format(n=cmap.name, a=minval, b=maxval),
        cmap(np.linspace(minval, maxval, n))
    )
    return new_cmap


class FeaturePerfOverheadComparisionTable(Table, table_name="fperf_overhead"):
    """Table that compares overhead of different feature performance measurement
    approaches."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()
        profilers: tp.List[Profiler] = [VXray(), PIMTracer(), EbpfTraceTEF()]

        # Data aggregation
        full_precision_df = load_precision_data(case_studies, profilers)
        full_precision_df.sort_values(["CaseStudy"], inplace=True)

        precision_df = full_precision_df[[
            "CaseStudy", "precision", "recall", "Profiler", "f1_score"
        ]]
        # aggregate multiple revisions
        precision_df = precision_df.groupby(['CaseStudy', "Profiler"],
                                            as_index=False).agg({
                                                'precision': 'mean',
                                                'recall': 'mean',
                                                'f1_score': 'mean'
                                            })
        print(f"precision_df=\n{precision_df}")

        overhead_df = load_overhead_data(case_studies, profilers)
        overhead_df = overhead_df[[
            "CaseStudy", "Profiler", "time", "memory", "overhead_time",
            "overhead_memory"
        ]]
        # print(f"{overhead_df=}")
        # TODO: double check and refactor
        overhead_df['overhead_time_rel'] = overhead_df['time'] / (
            overhead_df['time'] - overhead_df['overhead_time']
        ) * 100 - 100

        overhead_df['overhead_memory_rel'] = overhead_df['memory'] / (
            overhead_df['memory'] - overhead_df['overhead_memory']
        ) * 100 - 100
        overhead_df['overhead_memory_rel'].replace([np.inf, -np.inf],
                                                   np.nan,
                                                   inplace=True)
        print(f"{overhead_df=}")

        # Merge with precision data
        merged_df = pd.merge(
            precision_df, overhead_df, on=["CaseStudy", "Profiler"]
        )
        print(f"merged_df=\n{merged_df}")

        pivot_df = merged_df.pivot(
            index='CaseStudy',
            columns='Profiler',
            values=[
                'precision', 'recall', 'overhead_time_rel',
                'overhead_memory_rel'
            ]
        )

        # print(f"pivot_df=\n{pivot_df}")
        # print(f"{pivot_df.columns=}")
        pivot_df = pivot_df.swaplevel(0, 1, 1).sort_index(axis=1)

        # print(f"pivot_df=\n{pivot_df}")
        columns = [
            'precision', 'recall', 'overhead_time_rel', 'overhead_memory_rel'
        ]
        pivot_df = pivot_df.reindex([
            (prof.name, c) for prof in profilers for c in columns
        ],
                                    axis=1)
        print(f"pivot_df=\n{pivot_df}")

        # print(f"{pivot_df.columns=}")

        pivot_df.loc["Total"] = pivot_df.mean()
        print(f"pivot_df=\n{pivot_df}")

        # Rename columns
        overhead_time_c_name = "$\Delta$ Time $(\%)$"
        overhead_memory_c_name = "$\Delta$ Mem $(\%)$"
        pivot_df = pivot_df.rename(
            columns={
                "precision": "Precision",
                "recall": "Recall",
                "overhead_time_rel": overhead_time_c_name,
                "overhead_memory_rel": overhead_memory_c_name,
            }
        )

        style: pd.io.formats.style.Styler = pivot_df.style
        kwargs: tp.Dict[str, tp.Any] = {}

        def add_extras(doc: Document) -> None:
            doc.packages.append(Package("amsmath"))
            doc.packages.append(Package("amssymb"))

        if table_format.is_latex():
            style.format(precision=2)

            ryg_map = plt.get_cmap('RdYlGn')
            ryg_map = cmap_map(lambda x: x / 1.2 + 0.2, ryg_map)

            style.background_gradient(
                cmap=ryg_map,
                subset=[(prof.name, 'Precision') for prof in profilers],
                vmin=0.0,
                vmax=1.0,
            )
            style.background_gradient(
                cmap=ryg_map,
                subset=[(prof.name, 'Recall') for prof in profilers],
                vmin=0.0,
                vmax=1.0,
            )

            gray_map = plt.get_cmap('binary')
            gray_map = truncate_colormap(gray_map, 0, 0.6, 200)
            style.background_gradient(
                cmap=gray_map,
                subset=[(prof.name, overhead_time_c_name) for prof in profilers
                       ],
                vmin=0.0,
                vmax=100.0,
            )

            style.background_gradient(
                cmap=gray_map,
                subset=[
                    (prof.name, overhead_memory_c_name) for prof in profilers
                ],
                vmin=0.0,
                vmax=100.0,
            )

            kwargs["convert_css"] = True
            kwargs["column_format"] = "l" + "".join(["rrrr" for _ in profilers])
            kwargs["hrules"] = True
            kwargs["multicol_align"] = "c"

        return dataframe_to_table(
            data=pivot_df,
            table_format=table_format,
            style=style,
            wrap_table=wrap_table,
            wrap_landscape=True,
            document_decorator=add_extras,
            **kwargs
        )


class FeaturePerfOverheadComparisionTableGenerator(
    TableGenerator, generator_name="fperf-overhead-comp", options=[]
):
    """Generator for `FeaturePerfOverheadTable`."""

    def generate(self) -> tp.List[Table]:
        return [
            FeaturePerfOverheadComparisionTable(
                self.table_config, **self.table_kwargs
            )
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
