import typing as tp

import seaborn as sns
from matplotlib import pyplot as plt

from varats.data.databases.feature_perf_precision_database import (
    Profiler,
    VXray,
    PIMTracer,
    EbpfTraceTEF,
    Baseline,
    load_accuracy_data,
)
from varats.experiments.vara.ma_abelt_experiments import (
    BlackBoxBaselineRunnerAccuracy,
    PIMProfileRunnerPrecision,
    TEFProfileRunnerPrecision,
    EbpfTraceTEFProfileRunnerPrecision,
)
from varats.paper.paper_config import get_loaded_paper_config
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import FullCommitHash


class PerfAccuracyDistPlot(Plot, plot_name='fperf_accuracy_dist'):
    """Accuracy plot that plots the measuring accuracy for feature regressions
    across all feature regions for different profilers."""

    def plot(self, view_mode: bool) -> None:
        if "case_study" in self.plot_kwargs:
            case_studies = [self.plot_kwargs["case_study"]]
        else:
            case_studies = get_loaded_paper_config().get_all_case_studies()

        profilers: tp.List[Profiler] = [
            Baseline(experiment=BlackBoxBaselineRunnerAccuracy),
            VXray(experiment=TEFProfileRunnerPrecision),
            PIMTracer(experiment=PIMProfileRunnerPrecision),
            EbpfTraceTEF(experiment=EbpfTraceTEFProfileRunnerPrecision)
        ]

        # Data aggregation
        df = load_accuracy_data(case_studies, profilers)
        df.sort_values(["CaseStudy"], inplace=True)

        if "case_study" in self.plot_kwargs:
            df = df[df["CaseStudy"] ==
                    self.plot_kwargs["case_study"].project_name]

        df = df.melt(
            id_vars=['CaseStudy', 'PatchList', 'ConfigID', 'Profiler'],
            value_vars=['Epsilon', 'epsilon'],
            var_name='metric',
            value_name="value"
        )

        colors = sns.color_palette("Paired", len(profilers) * 2)
        _, axes = plt.subplots(ncols=len(profilers), nrows=1, sharey=True)

        for idx, profiler in enumerate(profilers):
            ax = axes[idx]
            color_slice = colors[idx * 2:idx * 2 + 2]
            data_slice = df[df['Profiler'] == profiler.name]

            ax.invert_yaxis()

            sns.violinplot(
                data=data_slice,
                x='Profiler',
                y='value',
                hue='metric',
                inner=None,
                cut=0,
                split=True,
                palette=color_slice,
                linewidth=1,
                ax=ax
            )

            ax.get_legend().remove()

            ax.set_ylabel(None)
            ax.set_xlabel(None)
            ax.tick_params(axis='x', labelsize=10, pad=8, length=6, width=1)

            if idx == 0:
                ax.set_ylim(-0.1, 1.1)
                if "case_study" in self.plot_kwargs:
                    nm = self.plot_kwargs["case_study"].project_name

                    if nm == "DunePerfRegression":
                        ax.set_ylim(-1, 11)
                ax.tick_params(axis='y', labelsize=10)
                ax.tick_params(axis='y', width=1, length=3)
            else:
                ax.tick_params(left=False)

        plt.subplots_adjust(wspace=.0)

        if "case_study" in self.plot_kwargs:
            plt.title = self.plot_kwargs["case_study"].project_name

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class PerfAccuracyDistPlotGenerator(
    PlotGenerator, generator_name="fperf-accuracy-dist", options=[]
):
    """Generates accuracy distribution plot."""

    def generate(self) -> tp.List[Plot]:

        return [
            PerfAccuracyDistPlot(
                self.plot_config, **self.plot_kwargs, case_study=cs
            ) for cs in get_loaded_paper_config().get_all_case_studies()
        ]
