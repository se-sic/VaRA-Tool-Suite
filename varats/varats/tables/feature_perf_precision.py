"""Module for the FeaturePerfPrecision tables."""
import json
import re
import typing as tp
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from benchbuild.utils.cmd import git, mkdir
from matplotlib import colors
from plumbum import local
from pylatex import Document, Package

from varats.data.databases.feature_perf_precision_database import (
    get_patch_names,
    get_regressing_config_ids_gt,
    map_to_positive,
    map_to_negative,
    Profiler,
    VXray,
    PIMTracer,
    EbpfTraceTEF,
    compute_profiler_predictions,
    load_precision_data,
    load_overhead_data,
    get_regressed_features_gt,
)
from varats.data.metrics import ConfusionMatrix
from varats.data.reports.tef_feature_identifier_report import (
    TEFFeatureIdentifierReport,
)
from varats.experiments.vara.ma_abelt_experiments import (
    PIMProfileRunnerPrecision,
    EbpfTraceTEFProfileRunnerPrecision,
    TEFProfileRunnerPrecision,
)
from varats.experiments.vara.tef_region_identifier import TEFFeatureIdentifier
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import get_local_project_git_path
from varats.report.multi_patch_report import MultiPatchReport
from varats.report.tef_report import TEFReportAggregate
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.utils.git_util import calc_repo_loc, ChurnConfig
from varats.utils.settings import bb_cfg


def cmap_map(
    function, cmap: colors.LinearSegmentedColormap
) -> colors.LinearSegmentedColormap:
    """
    Applies function (which should operate on vectors of shape 3: [r, g, b]), on
    colormap cmap.

    This routine will break any discontinuous points in a colormap.
    """
    c_dict = cmap._segmentdata  # pylint: disable=protected-access  # type: ignore
    step_dict: tp.Dict[str, tp.List[tp.Any]] = {}

    # First get the list of points where the segments start or end
    for key in ('red', 'green', 'blue'):
        step_dict[key] = list(map(lambda x: x[0], c_dict[key]))
    step_list = sum(step_dict.values(), [])
    step_array = np.array(list(set(step_list)))

    # Then compute the LUT, and apply the function to the LUT
    def reduced_cmap(step) -> np.ndarray:
        return np.array(cmap(step)[0:3])

    old_lut = np.array(list(map(reduced_cmap, step_array)))
    new_lut = np.array(list(map(function, old_lut)))

    # Now try to make a minimal segment definition of the new LUT
    c_dict = {}
    for i, key in enumerate(['red', 'green', 'blue']):
        this_c_dict = {}
        for j, step in enumerate(step_array):
            if step in step_dict[key]:
                this_c_dict[step] = new_lut[j, i]
            elif new_lut[j, i] != old_lut[j, i]:
                this_c_dict[step] = new_lut[j, i]
        colorvector = list(map(lambda x: x + (x[1],), this_c_dict.items()))
        colorvector.sort()
        c_dict[key] = colorvector

    return colors.LinearSegmentedColormap('colormap', c_dict, 1024)


class FeaturePerfPrecisionTable(Table, table_name="fperf_precision"):
    """Table that compares the precision of different feature performance
    measurement approaches."""

    @staticmethod
    def _prepare_data_table(
        case_studies: tp.List[CaseStudy], profilers: tp.List[Profiler]
    ):
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
                        len(map_to_positive(ground_truth))
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
                            map_to_positive(ground_truth),
                            map_to_negative(ground_truth),
                            map_to_positive(predicted),
                            map_to_negative(predicted)
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

        return pd.concat([df, pd.DataFrame(table_rows)])

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """Setup performance precision table."""
        case_studies = get_loaded_paper_config().get_all_case_studies()
        profilers: tp.List[Profiler] = [VXray(), PIMTracer()]

        # Data aggregation
        df = self._prepare_data_table(case_studies, profilers)
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

        print(f"{df=}")

        # Table config
        style: pd.io.formats.style.Styler = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["hrules"] = True
            column_format = "l|rr"
            for _ in profilers:
                column_format += "|rrr"
            kwargs["column_format"] = column_format
            kwargs["multicol_align"] = "|c"
            # pylint: disable=line-too-long
            kwargs[
                "caption"
            ] = f"""Localization precision of different performance profiling approaches to detect configuration-specific performance regression detection.
On the left, we show the amount of different configurations ({symb_configs}) analyzed and the amount of regressed configurations ({symb_regressed_configs}), determined through our baseline measurements.
Furthermore, the table depicts for each profiler, precision ({symb_precision}), recall ({symb_recall}), and balanced accuracy ({symb_b_accuracy}).
"""
            # pylint: enable=line-too-long
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


class FeaturePerfWBPrecisionTable(Table, table_name="fperf-wb-precision"):

    @staticmethod
    def _get_patches_for_patch_lists(
        project_name: str, config_id: int, profiler: Profiler
    ):
        result_folder_template = "{result_dir}/{project_dir}"

        vara_result_folder = result_folder_template.format(
            result_dir=str(bb_cfg()["varats"]["outfile"]),
            project_dir=project_name
        )

        mkdir("-p", vara_result_folder)

        json_path = Path(
            vara_result_folder
        ) / f"{config_id}-{profiler.experiment.shorthand()}.json"

        with open(json_path, "r") as f:
            p_lists = json.load(f)

        return {name: patches for name, patches in p_lists}

    @staticmethod
    def _prepare_data_table(
        case_studies: tp.List[CaseStudy], profilers: tp.List[Profiler]
    ):
        table_rows = []

        for cs in case_studies:
            rev = cs.revisions[0]
            cs_rows = []

            for config_id in cs.get_config_ids_for_revision(rev):
                # Load ground truth data
                ground_truth_report_files = get_processed_revisions_files(
                    cs.project_name,
                    TEFFeatureIdentifier,
                    TEFFeatureIdentifierReport,
                    get_case_study_file_name_filter(cs),
                    config_id=config_id
                )

                if len(ground_truth_report_files) != 1:
                    print("Invalid number of reports from TEFIdentifier")
                    continue

                ground_truth_report = TEFFeatureIdentifierReport(
                    ground_truth_report_files[0].full_path()
                )

                # Load the patch lists. While we technically have different files for each profiler, the contents are identical. The patch selection only depends on the configuration and project
                patch_lists = FeaturePerfWBPrecisionTable._get_patches_for_patch_lists(
                    cs.project_name, config_id, profilers[0]
                )

                for list_name in patch_lists:
                    new_row = {
                        'CaseStudy': cs.project_name,
                        'PatchList': list_name,
                        'ConfigID': config_id
                    }
                    # Get all patches contained in patch list
                    patches = patch_lists[list_name]

                    for profiler in profilers:
                        report_files = get_processed_revisions_files(
                            cs.project_name,
                            profiler.experiment,
                            profiler.report_type,
                            get_case_study_file_name_filter(cs),
                            config_id=config_id
                        )

                        if len(report_files) != 1:
                            print("Should only be one")
                            continue
                            # raise AssertionError("Should only be one")

                        report_file = MultiPatchReport(
                            report_files[0].full_path(), TEFReportAggregate
                        )

                        ground_truth = get_regressed_features_gt(
                            report_file.get_baseline_report().reports(),
                            ground_truth_report, patches
                        )

                        predicted = profiler.get_feature_regressions(
                            report_files[0], list_name
                        )

                        results = ConfusionMatrix(
                            map_to_positive(ground_truth),
                            map_to_negative(ground_truth),
                            map_to_positive(predicted),
                            map_to_negative(predicted)
                        )

                        new_row[f"{profiler.name}_precision"
                               ] = results.precision()
                        new_row[f"{profiler.name}_recall"] = results.recall()
                        new_row[f"{profiler.name}_baccuracy"
                               ] = results.balanced_accuracy()
                        new_row[f"RegressedFeatures"] = len(
                            map_to_positive(ground_truth)
                        )

                    cs_rows.append(new_row)

            cs_df = pd.DataFrame(cs_rows)

            new_row = {
                'CaseStudy': cs.project_name,
                '# f-Regressions': cs_df["RegressedFeatures"].sum()
            }

            for profiler in profilers:
                new_row[f"{profiler.name}_precision"] = cs_df[
                    f"{profiler.name}_precision"].mean()
                new_row[f"{profiler.name}_recall"] = cs_df[
                    f"{profiler.name}_recall"].mean()
                new_row[f"{profiler.name}_baccuracy"] = cs_df[
                    f"{profiler.name}_baccuracy"].mean()

            table_rows.append(new_row)

        return pd.DataFrame(table_rows)

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()
        profilers: tp.List[Profiler] = [
            VXray(experiment=TEFProfileRunnerPrecision),
            PIMTracer(experiment=PIMProfileRunnerPrecision),
            EbpfTraceTEF(experiment=EbpfTraceTEFProfileRunnerPrecision)
        ]

        df = self._prepare_data_table(case_studies, profilers)
        df.sort_values(["CaseStudy"], inplace=True)

        print(f"{df=}")

        return dataframe_to_table(
            df, table_format, wrap_table=wrap_table, wrap_landscape=True
        )


class FeaturePerfWBPrecisionTableGenerator(
    TableGenerator, generator_name="fperf-wb-precision", options=[]
):
    """Generator for 'FeaturePerfWBPrecisionTable'."""

    def generate(self) -> tp.List[Table]:
        return [
            FeaturePerfWBPrecisionTable(self.table_config, **self.table_kwargs)
        ]


def truncate_colormap(
    cmap: colors.Colormap,
    minval: float = 0.0,
    maxval: float = 1.0,
    n: int = 100
) -> colors.LinearSegmentedColormap:
    """
    Truncates a given color map to a specific range and number of elements.

    Args:
        cmap: the original colormap
        minval: smallest color value
        maxval: largest color value
        n: number of colors that should be in the map

    Returns: color map truncated to the given parameters
    """
    new_cmap = colors.LinearSegmentedColormap.from_list(
        f"trunc({cmap.name},{minval:.2f},{maxval:.2f})",
        cmap(np.linspace(minval, maxval, n))
    )
    return new_cmap


class FeaturePerfOverheadComparisionTable(Table, table_name="fperf_overhead"):
    """Table that compares overhead of different feature performance measurement
    approaches."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """Setup performance overhead comparision table."""
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

        # Merge with precision data
        merged_df = pd.merge(
            precision_df, overhead_df, on=["CaseStudy", "Profiler"]
        )

        pivot_df = merged_df.pivot(
            index='CaseStudy',
            columns='Profiler',
            values=[
                'precision', 'recall', 'overhead_time_rel',
                'overhead_memory_rel', 'overhead_memory'
            ]
        )

        pivot_df = pivot_df.swaplevel(0, 1, 1).sort_index(axis=1)

        columns = [
            'precision', 'recall', 'overhead_time_rel', 'overhead_memory_rel',
            'overhead_memory'
        ]
        pivot_df = pivot_df.reindex([
            (prof.name, c) for prof in profilers for c in columns
        ],
                                    axis=1)

        pivot_df.loc["Total"] = pivot_df.mean()

        # Rename columns
        # pylint: disable=anomalous-backslash-in-string
        overhead_time_c_name = "$\Delta$ Time $(\%)$"
        overhead_memory_c_name = "$\Delta$ Mem $(\%)$"
        overhead_memory_val_c_name = "$\Delta$ Mem $(Kbyte)$"
        # pylint: enable=anomalous-backslash-in-string
        pivot_df = pivot_df.rename(
            columns={
                "precision": "Precision",
                "recall": "Recall",
                "overhead_time_rel": overhead_time_c_name,
                "overhead_memory_rel": overhead_memory_c_name,
                "overhead_memory": overhead_memory_val_c_name,
            }
        )

        style: pd.io.formats.style.Styler = pivot_df.style
        kwargs: tp.Dict[str, tp.Any] = {}

        def add_extras(doc: Document) -> None:
            doc.packages.append(Package("amsmath"))
            doc.packages.append(Package("amssymb"))

        if table_format.is_latex():
            mv_columns = [
                (prof.name, overhead_memory_val_c_name) for prof in profilers
            ]
            style.format({col: "{:.0f}" for col in mv_columns}, precision=2)

            ryg_map = cmap_map(lambda x: x / 1.2 + 0.2, plt.get_cmap('RdYlGn'))

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
            kwargs["column_format"] = "l" + "".join([
                "rrrrr" for _ in profilers
            ])
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

    @staticmethod
    def _calc_folder_locs_dune(repo_path: Path, rev_range: str) -> int:
        dune_sub_projects = [
            "dune-alugrid", "dune-common", "dune-functions", "dune-geometry",
            "dune-grid", "dune-istl", "dune-localfunctions",
            "dune-multidomaingrid", "dune-pdelab", "dune-typetree",
            "dune-uggrid"
        ]
        total_locs = 0

        total_locs += calc_repo_loc(repo_path, rev_range)

        for sub_project in dune_sub_projects:
            sub_project_path = repo_path / sub_project
            # TODO: get sub_rpoject hashes
            locs = calc_repo_loc(sub_project_path, "HEAD")
            # print(f"Calculated {locs} for {sub_project_path}")
            total_locs += locs

        return total_locs

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
                if src_folder.endswith(
                    "projects/SynthCTTemplateSpecialization"
                ):
                    src_folder = "projects/SynthCTSpecialization"
                locs = self._calc_folder_locs(
                    project_git_path, rev.hash, src_folder
                )
            elif case_study.project_cls.NAME == "DunePerfRegression":
                locs = self._calc_folder_locs_dune(project_git_path, rev.hash)
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
