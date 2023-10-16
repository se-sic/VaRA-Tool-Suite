"""Example table that uses different workloads and visualizes the time it took
to run them."""
import typing as tp
import re

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import numpy as np

import varats.paper.paper_config as PC
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plot.plots import PlotGenerator
from varats.data.reports.instrumentation_verifier_report import (
    InstrVerifierReport,
)
from varats.report.report import ReportFilepath
from varats.revision.revisions import get_all_revisions_files
from varats.ts_utils.click_param_types import REQUIRE_EXPERIMENT_TYPE
from varats.utils.git_util import FullCommitHash


class InstrumentationVerifierOverviewBudgetPlot(
    Plot, plot_name="instrumentation_verifier_overview_budget"
):

    def plot(self, view_mode: bool) -> None:
        self._generate_plot(**self.plot_kwargs)

    @staticmethod
    def _generate_plot(**kwargs: tp.Any) -> None:
        case_study = kwargs["case_study"]
        experiment = kwargs["experiment_type"]

        revisions_files: tp.List[ReportFilepath] = get_all_revisions_files(
            case_study.project_name, experiment, only_newest=False
        )

        reports: tp.List[InstrVerifierReport] = [
            InstrVerifierReport(rev_file.full_path())
            for rev_file in revisions_files
        ]

        if len(reports) == 0:
            raise PlotDataEmpty()

        rows = []

        for report in reports:
            budget = 0
            for cf in report.metadata()["cflags"]:
                if "budget" not in cf:
                    continue

                budget = int(cf.split("=")[1])

            for binary in report.binaries():
                rows.append({
                    "binary": binary,
                    "budget": budget,
                    "enters": report.num_enters(binary),
                    "leaves": report.num_leaves(binary),
                    "unclosed_enters": report.num_unclosed_enters(binary),
                    "unentered_leaves": report.num_unentered_leaves(binary)
                })

        df = pd.DataFrame(rows)

        binaries = df["binary"].unique()
        fig, axs = plt.subplots((1 + len(binaries)) // 2, 2 - len(binaries) % 2, constrained_layout=True)
        fig.suptitle(
            f"Results of {experiment.NAME} by budget for case study {case_study.project_name}"
        )

        for i, binary in enumerate(binaries):
            if len(binaries) == 1:
                ax = axs
            elif len(binaries) == 2:
                ax = axs[i % 2]
            else:
                x, y = divmod(i, 2)
                ax = axs[x, y]

            d = df[df["binary"] == binary].sort_values("budget")

            num_enters_arr = np.array(d["enters"])
            num_leaves_arr = np.array(d["leaves"])
            num_unclosed_enters_arr = np.array(d["unclosed_enters"])
            num_unentered_leaves_arr = np.array(d["unentered_leaves"])

            num_enters_arr = num_enters_arr - num_unclosed_enters_arr
            num_leaves_arr = num_leaves_arr - num_unentered_leaves_arr

            X = np.arange(len(d["budget"]))

            ax.bar(X, num_enters_arr, label="#Enters")
            ax.bar(X, num_leaves_arr, label="#Leaves", bottom=num_enters_arr)
            ax.bar(
                X,
                num_unclosed_enters_arr,
                label="#Unclosed Enters",
                bottom=num_enters_arr + num_leaves_arr
            )
            ax.bar(
                X,
                num_unentered_leaves_arr,
                label="#Unentered Leaves",
                bottom=num_enters_arr + num_leaves_arr + num_unclosed_enters_arr
            )

            ax.set_ylabel("# Events")
            ax.set_xlabel("Budget")
            ax.set_xticks(X, labels=d["budget"])
            ax.set_title(binary)

        fig.legend(
            labels=[
                "Closed enters", "Entered leaves", "Unclosed enters",
                "Unentered leaves"
            ]
        )
        sns.despine()

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class CompareRuntimesBudgetPlotCSGenerator(
    PlotGenerator,
    generator_name="iv-ce-overview-budget-plot",
    options=[REQUIRE_EXPERIMENT_TYPE]
):

    def generate(self) -> tp.List[Plot]:
        return [
            InstrumentationVerifierOverviewBudgetPlot(
                self.plot_config, case_study=cs, **self.plot_kwargs
            ) for cs in PC.get_paper_config().get_all_case_studies()
        ]
