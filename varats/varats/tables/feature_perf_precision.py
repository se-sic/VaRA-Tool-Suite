"""Module for the FeaturePerfPrecision tables."""
import re
import typing as tp

import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
import pandas as pd
from benchbuild.utils.cmd import git
from matplotlib import colors
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
    compute_profiler_predictions,
    load_precision_data,
    load_overhead_data,
)
from varats.data.metrics import ConfusionMatrix
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import get_local_project_repo
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.cli_util import make_cli_option
from varats.utils.git_util import calc_repo_loc, ChurnConfig, RepositoryHandle

SYNTH_CATEGORIES = [
    "Static Analysis", "Dynamic Analysis", "Configurability",
    "Implementation Pattern"
]


def compute_cs_category_grouping(case_study_name: str) -> str:
    """Mapping function to transform individual project names to their synthtic
    categories."""
    if case_study_name.startswith("SynthSA"):
        return "Static Analysis"

    if case_study_name.startswith("SynthDA"
                                 ) or case_study_name.startswith("SynthOV"):
        return "Dynamic Analysis"

    if case_study_name.startswith("SynthFeature"):
        return "Configurability"

    if case_study_name.startswith("SynthCT"
                                 ) or case_study_name.startswith("SynthIP"):
        return "Implementation Pattern"

    return case_study_name


def cmap_map(
    function: tp.Callable[[npt.NDArray[np.float64]], npt.NDArray[np.float64]],
    cmap: colors.LinearSegmentedColormap
) -> colors.LinearSegmentedColormap:
    """
    Applies function (which should operate on vectors of shape 3: [r, g, b]), on
    colormap cmap.

    This routine will break any discontinuous points in a colormap.
    """
    # pylint: disable=protected-access
    c_dict = cmap._segmentdata  # type: ignore
    # pylint: enable=protected-access
    step_dict: tp.Dict[str, tp.List[tp.Any]] = {}

    # First get the list of points where the segments start or end
    for key in ('red', 'green', 'blue'):
        step_dict[key] = list(map(lambda x: x[0], c_dict[key]))
    step_list = sum(step_dict.values(), [])
    step_array = np.array(list(set(step_list)))

    # Then compute the LUT, and apply the function to the LUT
    def reduced_cmap(step: np.float64) -> npt.NDArray:
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
    ) -> pd.DataFrame:
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

        return pd.concat([df, pd.DataFrame(table_rows)])

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """Setup performance precision table."""
        case_studies = get_loaded_paper_config().get_all_case_studies()
        profilers: tp.List[Profiler] = [VXray(), PIMTracer(), EbpfTraceTEF()]

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


GROUP_SYNTHETIC_OPTION = make_cli_option(
    "--group-synth",
    type=bool,
    default=False,
    help="Group synthetic case studies in tables."
)


class FeaturePerfPrecisionTableGenerator(
    TableGenerator,
    generator_name="fperf-precision",
    options=[GROUP_SYNTHETIC_OPTION]
):
    """Generator for `FeaturePerfPrecisionTable`."""

    def generate(self) -> tp.List[Table]:
        return [
            FeaturePerfPrecisionTable(self.table_config, **self.table_kwargs)
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

        if self.table_kwargs["group_synth"]:

            merged_df["CaseStudy"] = merged_df["CaseStudy"].apply(
                compute_cs_category_grouping
            )
            merged_df = merged_df.groupby(['CaseStudy', "Profiler"],
                                          as_index=False).agg({
                                              'precision': 'mean',
                                              'recall': 'mean',
                                              'overhead_time': 'mean',
                                              'overhead_time_rel': 'mean',
                                              'overhead_memory_rel': 'mean',
                                              'overhead_memory': 'mean'
                                          })

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

        # All means need to be computed before they are added as rows
        overall_mean = pivot_df.mean()
        if self.table_kwargs["group_synth"]:
            synth_mean = pivot_df.loc[pivot_df.index.isin(SYNTH_CATEGORIES)
                                     ].mean()
            real_world_mean = pivot_df.loc[~pivot_df.index.
                                           isin(SYNTH_CATEGORIES)].mean()

            pivot_df.loc["SynthMean"] = synth_mean
            pivot_df.loc["RealWorldMean"] = real_world_mean

        pivot_df.loc["OverallMean"] = overall_mean

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

            ryg_map = cmap_map(
                lambda x: x / 1.2 + 0.2,
                tp.cast(colors.LinearSegmentedColormap, plt.get_cmap('RdYlGn'))
            )

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
    TableGenerator,
    generator_name="fperf-overhead-comp",
    options=[GROUP_SYNTHETIC_OPTION]
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
    def _calc_folder_locs(
        repo: RepositoryHandle, rev_range: str, folder: str
    ) -> int:
        churn_config = ChurnConfig.create_c_style_languages_config()
        file_pattern = re.compile(
            "|".join(churn_config.get_extensions_repr(r"^.*\.", r"$"))
        )

        loc: int = 0
        files = repo(
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
    def _calc_folder_locs_dune(repo: RepositoryHandle, rev_range: str) -> int:
        dune_sub_projects = [
            "dune-alugrid", "dune-common", "dune-functions", "dune-geometry",
            "dune-grid", "dune-istl", "dune-localfunctions",
            "dune-multidomaingrid", "dune-pdelab", "dune-typetree",
            "dune-uggrid"
        ]
        total_locs = 0

        total_locs += calc_repo_loc(repo, rev_range)

        for sub_project in dune_sub_projects:
            sub_project_repo = RepositoryHandle(
                repo.worktree_path / sub_project
            )
            locs = calc_repo_loc(sub_project_repo, "HEAD")
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
            project_repo = get_local_project_repo(project_name)

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
                    project_repo, rev.hash, src_folder
                )
            elif case_study.project_cls.NAME == "DunePerfRegression":
                locs = self._calc_folder_locs_dune(project_repo, rev.hash)
            else:
                locs = calc_repo_loc(project_repo, rev.hash)

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
        df.index.name = 'CaseStudy'

        if self.table_kwargs["group_synth"]:
            df.index = df.index.map(compute_cs_category_grouping)

            df = df.groupby(df.index.name, as_index=True).agg({
                'NumConfig': 'sum',
                'Locs': 'sum',
                'Regressions': 'sum'
            })

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
