"""Module for the FeaturePerfPrecision plots."""
import random
import typing as tp

import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from matplotlib.text import Text

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
    load_precision_data,
    load_overhead_data,
)
from varats.data.metrics import ClassificationResults
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.plot.plot import Plot
from varats.plot.plots import PlotConfig, PlotGenerator
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
                'Profiler': prof
            }
            fake_rows.append(new_fake_row)

    return fake_rows


class PerfPrecisionPlot(Plot, plot_name='fperf_precision'):

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()
        profilers: tp.List[Profiler] = [VXray(), PIMTracer()]

        # Data aggregation
        df = pd.DataFrame()
        df = load_precision_data(case_studies, profilers)
        df = pd.concat([df, pd.DataFrame(get_fake_prec_rows())])
        df.sort_values(["CaseStudy"], inplace=True)
        print(f"{df=}")

        print(f"{df['Profiler']=}")
        grid = multivariate_grid(
            df,
            'precision',
            'recall',
            'Profiler',
            global_kde=False,
            alpha=0.7,
            legend=False,
            s=100
        )
        grid.ax_marg_x.set_xlim(0.0, 1.02)
        grid.ax_marg_y.set_ylim(0.0, 1.02)
        grid.ax_joint.legend([name for name, _ in df.groupby("Profiler")])

        grid.ax_joint.set_xlabel("Precision")
        grid.ax_joint.set_ylabel("Recall")
        grid.ax_joint.xaxis.label.set_size(20)
        grid.ax_joint.yaxis.label.set_size(20)

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
            n = -0.1 if prof == "PIMTracer" else 0.0
            x = random.random()
            y = random.random()
            z = random.random()
            new_fake_row = {
                'CaseStudy': "fake",
                'Patch': "fpatch",
                'Configs': 42,
                'RegressedConfigs': 21,
                'precision': x - n,
                'recall': y,
                'f1_score': z,
                'Profiler': prof
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
                'Profiler': prof,
                'overhead_time':
                    (random.random() * 4) * 100,  # random.randint(2, 230),
                'overhead_ctx': random.randint(2, 1230)
            }
            fake_rows.append(new_fake_row)

    return fake_rows


class PerfOverheadPlot(Plot, plot_name='fperf_overhead'):

    def __init__(
        self, target_metric, plot_config: PlotConfig, **kwargs: tp.Any
    ) -> None:
        super().__init__(plot_config, **kwargs)
        self.__target_metric = target_metric

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
        df = load_precision_data(case_studies, profilers)
        # df = pd.concat([df, pd.DataFrame(get_fake_prec_rows_overhead())])
        df.sort_values(["CaseStudy"], inplace=True)
        print(f"{df=}")

        sub_df = df[[
            "CaseStudy", "precision", "recall", "Profiler", "f1_score"
        ]]
        sub_df = sub_df.groupby(['CaseStudy', "Profiler"], as_index=False).agg({
            'precision': 'mean',
            'recall': 'mean',
            'f1_score': 'mean'
        })

        print(f"{sub_df=}")

        # other_df = self.other_frame()
        # other_df = pd.DataFrame()
        # other_df = pd.concat([
        #     other_df, pd.DataFrame(get_fake_overhead_better_rows())
        # ])
        # other_df = other_df.groupby(['CaseStudy', 'Profiler'])
        # print(f"other_df=\n{other_df}")
        other_df = load_overhead_data(case_studies, profilers)
        print(f"other_df=\n{other_df}")
        other_df['overhead_time_rel'] = other_df['time'] / (
            other_df['time'] - other_df['overhead_time']
        ) * 100

        other_df['overhead_ctx_rel'] = other_df['ctx'] / (
            other_df['ctx'] - other_df['overhead_ctx']
        ) * 100
        print(f"other_df=\n{other_df}")

        target_row = "f1_score"
        # target_row = "precision"

        # final_df = sub_df.join(other_df, on=["CaseStudy", "Profiler"])
        final_df = pd.merge(sub_df, other_df, on=["CaseStudy", "Profiler"])
        print(f"{final_df=}")

        if self.__target_metric == "time":
            plot_extra_name = "Time"
            x_values = "overhead_time_rel"
        elif self.__target_metric == "ctx":
            plot_extra_name = "Ctx"
            x_values = "overhead_ctx_rel"
        else:
            raise NotImplementedError()

        ax = sns.scatterplot(
            final_df,
            x=x_values,
            y=target_row,
            hue="Profiler",
            style='CaseStudy',
            alpha=0.5,
            s=100
        )

        print(f"{ax.legend()=}")
        print(f"{type(ax.legend())=}")
        print(f"{ax.legend().get_children()=}")
        print(f"{ax.legend().prop=}")
        print(f"{ax.legend().get_title()}")
        print(f"{ax.legend().get_lines()}")
        print(f"{ax.legend().get_patches()}")
        print(f"{ax.legend().get_texts()}")
        ax.legend().set_title("Walrus")

        for text_obj in ax.legend().get_texts():
            text_obj: Text

            text_obj.set_fontsize("small")
            print(f"{text_obj=}")
            if text_obj.get_text() == "Profiler":
                text_obj.set_text("Profilers")
                text_obj.set_fontweight("bold")

            if text_obj.get_text() == "CaseStudy":
                text_obj.set_text("Subject Systems")
                text_obj.set_fontweight("bold")

        # ax.legend().set_bbox_to_anchor((1, 0.5))

        # grid.ax_marg_x.set_xlim(0.0, 1.01)
        ax.set_xlabel(f"{plot_extra_name} Overhead in %")
        if target_row == "f1_score":
            ax.set_ylabel("F1-Score")

        # ax.set_ylim(np.max(final_df['overhead_time']) + 20, 0)
        ax.set_ylim(0.0, 1.02)
        # ax.set_xlim(0, np.max(final_df['overhead_time']) + 20)
        ax.set_xlim(np.max(final_df[x_values]) + 20, 0)
        # ax.set_xlim(1.01, 0.0)
        ax.xaxis.label.set_size(20)
        ax.yaxis.label.set_size(20)
        ax.tick_params(labelsize=15)

        prof_df = final_df[['Profiler', 'precision', x_values, 'f1_score'
                           ]].groupby('Profiler').agg(['mean', 'std'])
        prof_df.fillna(0, inplace=True)

        print(f"{prof_df=}")
        p = self.plot_pareto_frontier(
            prof_df[x_values]['mean'], prof_df[target_row]['mean'], maxX=False
        )
        # p = self.plot_pareto_frontier_std(
        #     prof_df['overhead_time']['mean'],
        #     prof_df[target_row]['mean'],
        #     prof_df['overhead_time']['std'],
        #     prof_df[target_row]['std'],
        #     maxX=False
        # )

        pf_x = [pair[0] for pair in p]
        pf_y = [pair[1] for pair in p]
        # pf_x_error = [pair[2] for pair in p]
        # pf_y_error = [pair[3] for pair in p]

        x_loc = prof_df[x_values]['mean']
        y_loc = prof_df[target_row]['mean']
        x_error = prof_df[x_values]['std']
        y_error = prof_df[target_row]['std']

        ax.errorbar(
            x_loc,  # pf_x,
            y_loc,  # pf_y,
            xerr=x_error,  # xerr=pf_x_error,
            yerr=y_error,  # yerr=pf_y_error,
            fmt='none',
            color='grey',
            zorder=0,
            capsize=2,
            capthick=0.6,
            elinewidth=0.6
        )

        sns.scatterplot(
            prof_df,
            x=(x_values, 'mean'),
            y=(target_row, 'mean'),
            hue="Profiler",
            ax=ax,
            legend=False,
            s=100,
            zorder=2
        )

        # p = self.plot_pareto_frontier(
        #     final_df['precision'], final_df['overhead_time']
        # )

        #         print(f"""{pf_x=}
        # {pf_y=}
        # {pf_x_error=}
        # {pf_y_error=}
        # """)
        # plt.plot(pf_x, pf_y)
        sns.lineplot(
            x=pf_x,
            y=pf_y,
            ax=ax,
            color='firebrick',
            legend=False,
            linewidth=2.5,
            zorder=1
        )

        # def_totals = pd.DataFrame()
        # def_totals.loc['mean'] = [1, 2, 23]
        # print(f"{def_totals=}")

    def plot_pareto_frontier(self, Xs, Ys, maxX=True, maxY=True):
        """Pareto frontier selection process."""
        sorted_list = sorted([[Xs[i], Ys[i]] for i in range(len(Xs))],
                             reverse=maxX)
        print(f"{sorted_list=}")
        pareto_front = [sorted_list[0]]
        for pair in sorted_list[1:]:
            print(f"{pair=}")
            if maxY:
                if pair[1] >= pareto_front[-1][1]:
                    pareto_front.append(pair)
            else:
                if pair[1] <= pareto_front[-1][1]:
                    pareto_front.append(pair)

        return pareto_front

    def plot_pareto_frontier_std(
        self, Xs, Ys, Xstds, Ystds, maxX=True, maxY=True
    ):
        """Pareto frontier selection process."""
        sorted_list = sorted([
            [Xs[i], Ys[i], Xstds[i], Ystds[i]] for i in range(len(Xs))
        ],
                             reverse=maxX)
        print(f"{sorted_list=}")
        pareto_front = [sorted_list[0]]
        for pair in sorted_list[1:]:
            print(f"{pair=}")
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

        return [
            PerfOverheadPlot(metric, self.plot_config, **self.plot_kwargs)
            for metric in ["time", "ctx"]
        ]
