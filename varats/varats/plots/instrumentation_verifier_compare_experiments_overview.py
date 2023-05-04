"""Generate graphs that show an overview of the instrumentation verifier
experiment state for all case studies in the paper config."""

import typing as tp

import matplotlib.pyplot as plt
from matplotlib import ticker
import numpy as np

import varats.paper.paper_config as PC
from varats.data.reports.instrumentation_verifier_report import (
    InstrVerifierReport,
)
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plot.plots import PlotGenerator
from varats.report.report import ReportFilepath
from varats.revision.revisions import get_all_revisions_files
from varats.ts_utils.click_param_types import REQUIRE_MULTI_EXPERIMENT_TYPE
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import FullCommitHash
import itertools


class InstrumentationOverviewCompareExperimentsPlot(
    Plot, plot_name="instrumentation_overview_compare_experiments_plot"
):
    """
    Plot configuration for the instrumentation verifier experiment.

    This plot shows an overview of the instrumentation verifier state for all
    case studies in the paper config.
    """

    def plot(self, view_mode: bool) -> None:
        self._generate_plot(**self.plot_kwargs)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation

    @staticmethod
    def _generate_plot(**kwargs: tp.Any) -> None:
        case_study = kwargs['case_study']

        width = 0.25
        multiplicator = 0

        minor_labels = []
        minor_ticks = []

        _, ax = plt.subplots()

        for experiment in kwargs["experiment_type"]:

            revisions_files: tp.List[ReportFilepath] = get_all_revisions_files(
                case_study.project_name, experiment, only_newest=False
            )

            labels: tp.List[str] = []

            reports: tp.List[InstrVerifierReport] = [
                InstrVerifierReport(rev_file.full_path())
                for rev_file in revisions_files
            ]

            if len(reports) == 0:
                raise PlotDataEmpty()

            num_enters: tp.List[int] = []
            num_leaves: tp.List[int] = []
            num_unclosed_enters: tp.List[int] = []
            num_unentered_leaves: tp.List[int] = []

            for report in reports:
                for binary in report.binaries():
                    labels.append(f"{binary}")
                    num_enters.append(report.num_enters(binary),)
                    num_leaves.append(report.num_leaves(binary),)
                    num_unclosed_enters.append(
                        report.num_unclosed_enters(binary),
                    )
                    num_unentered_leaves.append(
                        report.num_unentered_leaves(binary),
                    )

            minor_labels.extend([
                x + "-" + y
                for x, y in zip(labels, itertools.repeat(experiment.NAME))
            ])
            ind = np.arange(len(num_enters))
            offset = width * multiplicator

            ax.bar(
                ind + offset,
                num_enters,
                width,
                color="tab:blue",
                edgecolor="black"
            )
            ax.bar(
                ind + offset,
                num_leaves,
                width,
                color="tab:orange",
                bottom=num_enters,
                edgecolor="black"
            )
            ax.bar(
                ind + offset,
                num_unclosed_enters,
                width,
                color="tab:cyan",
                edgecolor="black",
                bottom=[a + b for a, b in zip(num_enters, num_leaves)]
            )
            ax.bar(
                ind + offset,
                num_unentered_leaves,
                width,
                color="tab:olive",
                edgecolor="black",
                bottom=[
                    a + b + c for a, b, c in
                    zip(num_enters, num_leaves, num_unclosed_enters)
                ]
            )

            minor_ticks.extend(ind + offset)
            multiplicator += 1

        ax.set_ylabel("Number of events")
        ax.set_title(
            f"Instrumentation Verifier "
            f"Overview for {case_study.project_name}"
        )
        ax.legend()
        # ax.set_xticks(ind + width, labels=labels, rotation=30, ha="right")

        print(minor_labels)

        ax.set_xticks(
            minor_ticks,
            labels=minor_labels,
            rotation=30,
            ha="right",
        )

        plt.subplots_adjust(bottom=0.25)


class VerifierExperimentCompareOverviewGenerator(
    PlotGenerator,
    generator_name="iv-ce-overview-plot",
    options=[REQUIRE_MULTI_EXPERIMENT_TYPE]
):
    """Generates a single pc-overview plot for the current paper config."""

    def generate(self) -> tp.List[Plot]:
        return [
            InstrumentationOverviewCompareExperimentsPlot(
                self.plot_config, case_study=cs, **self.plot_kwargs
            ) for cs in PC.get_paper_config().get_all_case_studies()
        ]
