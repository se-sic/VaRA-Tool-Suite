"""Generate graphs that show an overview of the instrumentation verifier
experiment state for all case studies in the paper config."""

import typing as tp

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import varats.paper.paper_config as PC
from varats.data.reports.instrumentation_verifier_report import (
    InstrVerifierReport,
)
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plot.plots import PlotGenerator
from varats.report.report import ReportFilepath
from varats.revision.revisions import get_all_revisions_files
from varats.ts_utils.click_param_types import REQUIRE_MULTI_EXPERIMENT_TYPE, REQUIRE_MULTI_CASE_STUDY
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import FullCommitHash
import re
from varats.paper_mgmt.case_study import get_case_study_file_name_filter

starting_budget_command_regex = re.compile("RunInstrVerifierNaive([0-9]+)")


class InstrumentationOverviewCompareExperimentsBudgetLabelsPlot(
    Plot,
    plot_name="instrumentation_overview_compare_experiments_budget_labels_plot"
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

        rows = []

        for experiment in kwargs["experiment_type"]:
            revisions_files: tp.List[ReportFilepath] = get_all_revisions_files(
                case_study.project_name,
                experiment,
                InstrVerifierReport,
                get_case_study_file_name_filter(case_study),
                only_newest=False
            )

            reports: tp.List[InstrVerifierReport] = [
                InstrVerifierReport(rev_file.full_path())
                for rev_file in revisions_files
            ]

            if len(reports) == 0:
                raise PlotDataEmpty()

            budget = 0
            if (
                m := re.search(starting_budget_command_regex, experiment.NAME)
            ) is not None:
                budget = int(m.group(1))

            for report in reports:
                for binary in report.binaries():
                    rows.append({
                        "experiment": str(budget),
                        "binary": binary,
                        "enters": report.num_enters(binary),
                        "leaves": report.num_leaves(binary),
                        "unclosed_enters": report.num_unclosed_enters(binary),
                        "unentered_leaves": report.num_unentered_leaves(binary)
                    })

        df = pd.DataFrame(rows)
        df = df.drop(df[df["binary"] == "example"].index)
        binaries = df["binary"].unique()

        experiments = df["experiment"].unique()

        fig, axs = plt.subplots((1 + len(binaries)) // 2,
                                2 - len(binaries) % 2,
                                constrained_layout=True)

        for i, binary in enumerate(binaries):
            if len(binaries) == 1:
                ax = axs
            elif len(binaries) == 2:
                ax = axs[i % 2]
            else:
                x, y = divmod(i, 2)
                ax = axs[(x, y)]

            d = df[df["binary"] == binary]

            num_enters = np.array(d["enters"])
            num_leaves = np.array(d["leaves"])
            num_unclosed_enters = np.array(d["unclosed_enters"])
            num_unentered_leaves = np.array(d["unentered_leaves"])

            ax.bar(experiments, num_enters)
            ax.bar(
                experiments,
                num_leaves,
                bottom=num_enters,
            )
            ax.bar(
                experiments,
                num_unclosed_enters,
                bottom=num_enters + num_leaves
            )
            ax.bar(
                experiments,
                num_unentered_leaves,
                bottom=num_enters + num_leaves + num_unclosed_enters
            )

            ax.set_ylabel("Number of events")
            ax.set_xticks(ax.get_xticks(), ax.get_xticklabels(), rotation=45)
            ax.set_title(binary)

        fig.suptitle(
            f"Instrumentation Verifier "
            f"Overview for {case_study.project_name}"
        )
        fig.legend(
            labels=["Enters", "Leaves", "Unclosed enters", "Unentered leaves"]
        )


class VerifierExperimentCompareBudgetLabelsOverviewGenerator(
    PlotGenerator,
    generator_name="iv-ceb-overview-plot",
    options=[REQUIRE_MULTI_EXPERIMENT_TYPE, REQUIRE_MULTI_CASE_STUDY]
):
    """Generates a single pc-overview plot for the current paper config."""

    def generate(self) -> tp.List[Plot]:
        case_studies = self.plot_kwargs.pop("case_study")
        return [
            InstrumentationOverviewCompareExperimentsBudgetLabelsPlot(
                self.plot_config, case_study=cs, **self.plot_kwargs
            ) for cs in case_studies
        ]
