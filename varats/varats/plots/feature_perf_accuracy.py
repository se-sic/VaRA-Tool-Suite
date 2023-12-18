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

        print(f"{df.to_string()}")

        g = sns.displot(
            data=df[df["Features"] == "__ALL__"],
            x="epsilon",
            hue="Profiler",
            kind="kde",
            col="CaseStudy"
        )
        g.set_axis_labels("\u0190", "Density")
        g.set_titles("{col_name}")

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class PerfAccuracyDistPlotGenerator(
    PlotGenerator, generator_name="fperf-accuracy-dist", options=[]
):
    """Generates accuracy distribution plot."""

    def generate(self) -> tp.List[Plot]:

        return [PerfAccuracyDistPlot(self.plot_config, **self.plot_kwargs)]


class PerfWBAccuracyDistPlot(Plot, plot_name='fperf_wb_accuracy_dist'):
    """Accuracy plot that plots the measuring accuracy for feature regressions
    for individual feature regions for different profilers."""

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()
        profilers: tp.List[Profiler] = [
            VXray(experiment=TEFProfileRunnerPrecision),
            PIMTracer(experiment=PIMProfileRunnerPrecision),
            EbpfTraceTEF(experiment=EbpfTraceTEFProfileRunnerPrecision)
        ]

        # Data aggregation
        df = load_accuracy_data(case_studies, profilers)
        df.sort_values(["CaseStudy"], inplace=True)

        g = sns.displot(
            data=df[df["Features"] != "__ALL__"],
            x="epsilon",
            hue="Profiler",
            kind="kde",
            col="CaseStudy"
        )
        g.set_axis_labels("\u03b5", "Density")
        g.set_titles("{col_name}")

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class PerfWBAccuracyDistPlotGenerator(
    PlotGenerator, generator_name="fperf-wb-accuracy-dist", options=[]
):
    """Generates accuracy distribution plot."""

    def generate(self) -> tp.List[Plot]:

        return [
            PerfAccuracyDistPlot(
                self.plot_config,
                **self.plot_kwargs,
                plot_name='fperf-wb-accuracy-dist',
                case_study=cs
            ) for cs in get_loaded_paper_config().get_all_case_studies()
        ]
