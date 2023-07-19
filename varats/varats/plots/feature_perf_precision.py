"""Module for the FeaturePerfPrecision plots."""
import random
import typing as tp

import numpy as np
import pandas as pd
import seaborn as sns

from varats.data.databases.feature_perf_precision_database import (
    Profiler,
    get_regressing_config_ids_gt,
    VXray,
    PIMTracer,
    get_patch_names,
    map_to_positive_config_ids,
    map_to_negative_config_ids,
    compute_profiler_predictions,
    Baseline,
    OverheadData,
)
from varats.data.metrics import ClassificationResults
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.plots.scatter_plot_utils import multivariate_grid
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import FullCommitHash


def get_fake_prec_rows() -> tp.List[tp.Any]:
    fake_rows = []
    fake_prof = [("prof1", 10), ("prof2", 42)]
    for prof, seed in fake_prof:
        random.seed(seed)
        for _ in range(0, 3):
            x = random.random()
            y = random.random()
            new_fake_row = {
                'CaseStudy': "fake",
                'Patch': "fpatch",
                'Configs': 42,
                'RegressedConfigs': 21,
                'precision': x,
                'recall': y,
                'profiler': prof
            }
            fake_rows.append(new_fake_row)

    return fake_rows


class PerfPrecisionPlot(Plot, plot_name='fperf_precision'):

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()
        profilers: tp.List[Profiler] = [VXray(), PIMTracer()]

        # Data aggregation
        df = pd.DataFrame()
        table_rows_plot = []

        for case_study in case_studies:
            for patch_name in get_patch_names(case_study):
                rev = case_study.revisions[0]
                project_name = case_study.project_name

                ground_truth = get_regressing_config_ids_gt(
                    project_name, case_study, rev, patch_name
                )

                for profiler in profilers:
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

                    # TODO: multiple patch cycles
                    predicted = compute_profiler_predictions(
                        profiler, project_name, case_study,
                        case_study.get_config_ids_for_revision(rev), patch_name
                    )

                    if ground_truth and predicted:
                        results = ClassificationResults(
                            map_to_positive_config_ids(ground_truth),
                            map_to_negative_config_ids(ground_truth),
                            map_to_positive_config_ids(predicted),
                            map_to_negative_config_ids(predicted)
                        )

                        new_row['precision'] = results.precision()
                        new_row['recall'] = results.recall()
                        new_row['profiler'] = profiler.name
                        # new_row[f"{profiler.name}_precision"
                        #        ] = results.precision()
                        # new_row[f"{profiler.name}_recall"] = results.recall()
                        # new_row[f"{profiler.name}_baccuracy"
                        #        ] = results.balanced_accuracy()
                    else:
                        new_row['precision'] = np.nan
                        new_row['recall'] = np.nan
                        new_row['profiler'] = profiler.name

                    print(f"{new_row=}")
                    table_rows_plot.append(new_row)
                # df.append(new_row, ignore_index=True)

        df = pd.concat([df, pd.DataFrame(table_rows_plot)])
        df = pd.concat([df, pd.DataFrame(get_fake_prec_rows())])
        df.sort_values(["CaseStudy"], inplace=True)
        print(f"{df=}")

        print(f"{df['profiler']=}")
        grid = multivariate_grid(
            df,
            'precision',
            'recall',
            'profiler',
            global_kde=True,
            alpha=0.8,
            legend=False
        )
        grid.ax_marg_x.set_xlim(0.0, 1.01)
        grid.ax_marg_y.set_ylim(0.0, 1.01)
        grid.ax_joint.legend([name for name, _ in df.groupby("profiler")])

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class PerfPrecisionPlotGenerator(
    PlotGenerator, generator_name="fperf-precision", options=[]
):

    def generate(self) -> tp.List[Plot]:

        return [PerfPrecisionPlot(self.plot_config, **self.plot_kwargs)]


def get_fake_overhead_rows():
    fake_rows = []
    fake_prof = [("WXray", 10), ("PIMTracer", 42)]

    new_fake_row = {
        'CaseStudy': "fake",
        # 'Patch': "fpatch",
        'WithoutProfiler_mean_time': 42,
        'WithoutProfiler_mean_ctx': 2,
    }

    for prof, seed in fake_prof:
        random.seed(seed)
        # for _ in range(0, 3):
        new_fake_row[f"{prof}_time_mean"] = random.randint(2, 230)
        new_fake_row[f"{prof}_time_std"] = np.nan
        new_fake_row[f"{prof}_time_max"] = np.nan

        new_fake_row[f"{prof}_ctx_mean"] = random.randint(2, 1230)
        new_fake_row[f"{prof}_ctx_std"] = np.nan
        new_fake_row[f"{prof}_ctx_max"] = np.nan

    fake_rows.append(new_fake_row)

    return fake_rows


def get_fake_prec_rows_overhead() -> tp.List[tp.Any]:
    fake_rows = []
    fake_prof = [("WXray", 10), ("PIMTracer", 42)]
    for prof, seed in fake_prof:
        random.seed(seed)
        for _ in range(0, 3):
            n = 0.1 if prof == "PIMTracer" else 0.0
            x = random.random()
            y = random.random()
            new_fake_row = {
                'CaseStudy': "fake",
                'Patch': "fpatch",
                'Configs': 42,
                'RegressedConfigs': 21,
                'precision': x - n,
                'recall': y,
                'profiler': prof
            }
            fake_rows.append(new_fake_row)

    return fake_rows


def get_fake_overhead_better_rows():
    # case_study, profiler, overhead_time, overhead_ctx
    fake_cs = ["SynthSAContextSensitivity", "fake"]
    fake_prof = [("WXray", 10), ("PIMTracer", 12)]
    fake_rows = []

    for prof, seed in fake_prof:
        random.seed(seed)

        for cs in fake_cs:
            # extra = 1 if prof == 'PIMTracer' else 0

            new_fake_row = {
                'CaseStudy': cs,
                'profiler': prof,
                'overhead_time':
                    (random.random() * 4) * 100,  # random.randint(2, 230),
                'overhead_ctx': random.randint(2, 1230)
            }
            fake_rows.append(new_fake_row)

    return fake_rows


class PerfOverheadPlot(Plot, plot_name='fperf_overhead'):

    def other_frame(self):
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
        # print(f"{df=}")
        return df

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()
        profilers: tp.List[Profiler] = [VXray(), PIMTracer()]

        # Data aggregation
        df = pd.DataFrame()
        table_rows_plot = []

        for case_study in case_studies:
            for patch_name in get_patch_names(case_study):
                rev = case_study.revisions[0]
                project_name = case_study.project_name

                ground_truth = get_regressing_config_ids_gt(
                    project_name, case_study, rev, patch_name
                )

                for profiler in profilers:
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

                    # TODO: multiple patch cycles
                    predicted = compute_profiler_predictions(
                        profiler, project_name, case_study,
                        case_study.get_config_ids_for_revision(rev), patch_name
                    )

                    if ground_truth and predicted:
                        results = ClassificationResults(
                            map_to_positive_config_ids(ground_truth),
                            map_to_negative_config_ids(ground_truth),
                            map_to_positive_config_ids(predicted),
                            map_to_negative_config_ids(predicted)
                        )

                        new_row['precision'] = results.precision()
                        new_row['recall'] = results.recall()
                        new_row['profiler'] = profiler.name
                        # new_row[f"{profiler.name}_precision"
                        #        ] = results.precision()
                        # new_row[f"{profiler.name}_recall"] = results.recall()
                        # new_row[f"{profiler.name}_baccuracy"
                        #        ] = results.balanced_accuracy()
                    else:
                        new_row['precision'] = np.nan
                        new_row['recall'] = np.nan
                        new_row['profiler'] = profiler.name

                    print(f"{new_row=}")
                    table_rows_plot.append(new_row)
                # df.append(new_row, ignore_index=True)

        df = pd.concat([df, pd.DataFrame(table_rows_plot)])
        df = pd.concat([df, pd.DataFrame(get_fake_prec_rows_overhead())])
        df.sort_values(["CaseStudy"], inplace=True)
        print(f"{df=}")

        sub_df = df[["CaseStudy", "precision", "recall", "profiler"]]
        sub_df = sub_df.groupby(['CaseStudy', "profiler"], as_index=False).agg({
            'precision': 'mean',
            'recall': 'mean'
        })

        print(f"{sub_df=}")

        # other_df = self.other_frame()
        other_df = pd.DataFrame()
        other_df = pd.concat([
            other_df, pd.DataFrame(get_fake_overhead_better_rows())
        ])
        # other_df = other_df.groupby(['CaseStudy', 'profiler'])
        print(f"{other_df=}")

        # final_df = sub_df.join(other_df, on=["CaseStudy", "profiler"])
        final_df = pd.merge(sub_df, other_df, on=["CaseStudy", "profiler"])
        print(f"{final_df=}")

        ax = sns.scatterplot(
            final_df,
            x="precision",
            y='overhead_time',
            hue="profiler",
            style='CaseStudy',
            alpha=0.5
        )
        # grid.ax_marg_x.set_xlim(0.0, 1.01)
        ax.set_ylabel("Overhead in %")
        # ax.set_ylim(np.max(final_df['overhead_time']) + 20, 0)
        ax.set_ylim(0, np.max(final_df['overhead_time']) + 20)
        ax.set_xlim(0.0, 1.01)
        # ax.set_xlim(1.01, 0.0)
        ax.xaxis.label.set_size(25)
        ax.yaxis.label.set_size(25)
        ax.tick_params(labelsize=15)

        prof_df = final_df[['profiler', 'precision',
                            'overhead_time']].groupby('profiler').agg('mean')
        print(f"{prof_df=}")
        sns.scatterplot(
            prof_df,
            x="precision",
            y='overhead_time',
            hue="profiler",
            color='grey',
            ax=ax,
        )

        p = self.plot_pareto_frontier(
            final_df['precision'], final_df['overhead_time']
        )
        p = self.plot_pareto_frontier(
            prof_df['precision'], prof_df['overhead_time']
        )
        pf_x = [pair[0] for pair in p]
        pf_y = [pair[1] for pair in p]
        # plt.plot(pf_x, pf_y)
        sns.lineplot(x=pf_x, y=pf_y, ax=ax, color='grey')

        # def_totals = pd.DataFrame()
        # def_totals.loc['mean'] = [1, 2, 23]
        # print(f"{def_totals=}")

    def plot_pareto_frontier(self, Xs, Ys, maxX=True, maxY=True):
        """Pareto frontier selection process."""
        sorted_list = sorted([[Xs[i], Ys[i]] for i in range(len(Xs))],
                             reverse=maxY)
        pareto_front = [sorted_list[0]]
        for pair in sorted_list[1:]:
            if maxY:
                if pair[1] >= pareto_front[-1][1]:
                    pareto_front.append(pair)
            else:
                if pair[1] <= pareto_front[-1][1]:
                    pareto_front.append(pair)

        return pareto_front

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class PerfOverheadPlotGenerator(
    PlotGenerator, generator_name="fperf-overhead", options=[]
):

    def generate(self) -> tp.List[Plot]:

        return [PerfOverheadPlot(self.plot_config, **self.plot_kwargs)]
