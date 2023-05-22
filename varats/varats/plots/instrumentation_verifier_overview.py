"""Generate graphs that show an overview of the instrumentation verifier
experiment state for all case studies in the paper config."""

import typing as tp

import matplotlib.pyplot as plt
from matplotlib import ticker

import varats.paper.paper_config as PC
from varats.data.reports.instrumentation_verifier_report import (
    InstrVerifierReport,
)
from varats.experiment.experiment_util import VersionExperiment
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plot.plots import PlotGenerator
from varats.report.report import ReportFilepath
from varats.revision.revisions import get_all_revisions_files
from varats.ts_utils.click_param_types import REQUIRE_EXPERIMENT_TYPE
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import FullCommitHash


class InstrumentationOverviewPlot(
    Plot, plot_name="instrumentation_overview_plot"
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
        experiment_type: tp.Type[VersionExperiment] = kwargs['experiment_type']

        revisions_files: tp.List[ReportFilepath] = get_all_revisions_files(
            case_study.project_name, experiment_type, only_newest=False
        )

        _, ax = plt.subplots()

        # Ensure integer labels for the y-axis
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

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
                labels.append(
                    f"{report.filename.commit_hash}\nCID: "
                    f"{report.filename.config_id}\n{binary}"
                )
                num_enters.append(report.num_enters(binary))
                num_leaves.append(report.num_leaves(binary))
                num_unclosed_enters.append(report.num_unclosed_enters(binary))
                num_unentered_leaves.append(report.num_unentered_leaves(binary))

        ax.bar(labels, num_enters, label="#Enters")
        ax.bar(labels, num_leaves, label="#Leaves", bottom=num_enters)
        ax.bar(
            labels,
            num_unclosed_enters,
            label="#Unclosed Enters",
            bottom=[a + b for a, b in zip(num_enters, num_leaves)]
        )
        ax.bar(
            labels,
            num_unentered_leaves,
            label="#Unentered Leaves",
            bottom=[
                a + b + c
                for a, b, c in zip(num_enters, num_leaves, num_unclosed_enters)
            ]
        )

        ax.set_ylabel("Number of events")
        ax.set_title(
            f"Instrumentation Verifier "
            f"Overview for {case_study.project_name}"
        )
        ax.legend()
        plt.xticks(rotation=90, ha='right')
        plt.subplots_adjust(bottom=0.25)


class PaperConfigOverviewGenerator(
    PlotGenerator,
    generator_name="iv-overview-plot",
    options=[REQUIRE_EXPERIMENT_TYPE]
):
    """Generates a single pc-overview plot for the current paper config."""

    def generate(self) -> tp.List[Plot]:
        return [
            InstrumentationOverviewPlot(
                self.plot_config, case_study=cs, **self.plot_kwargs
            ) for cs in PC.get_paper_config().get_all_case_studies()
        ]
