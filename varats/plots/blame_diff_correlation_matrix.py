"""
Module for drawing commit-data metrics plots.

    - scatter-plot matrix
"""
import abc
import typing as tp

import matplotlib.pyplot as plt
import seaborn as sns

from varats.data.databases.blame_diff_metrics_database import (
    BlameDiffMetricsDatabase)
from varats.data.reports.commit_report import CommitMap
from varats.plots.plot import Plot


class BlameDiffCorrelationMatrix(Plot):
    """
    Draws a scatter-plot matrix for blame-data metrics, comparing the
    differente independen and dependen variables.
    """

    NAME = "b_correlation_matrix"

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    @abc.abstractmethod
    def plot(self, view_mode: bool) -> None:
        """Plot the current plot to a file"""
        commit_map: CommitMap = self.plot_kwargs['get_cmap']()
        case_study = self.plot_kwargs.get('plot_case_study', None)
        project_name = self.plot_kwargs["project"]

        sns.set(style="ticks", color_codes=True)

        df = BlameDiffMetricsDatabase.get_data_for_project(
            project_name, ["revision", "churn_total", "diff_ci_total", "year"],
            commit_map, case_study)
        df.set_index('revision', inplace=True)

        df.drop(df[df.churn_total == 0].index, inplace=True)

        sns.pairplot(
            df, hue="year",
            diag_kind="hist")  # , vars=["churn_total", "diff_ci_total"])
        # grid = sns.PairGrid(df,
        #                     x_vars=["churn_total", "diff_ci_total"],
        #                     y_vars=["churn_total", "diff_ci_total"])

    def show(self) -> None:
        """Show the current plot"""
        self.plot(True)
        plt.show()

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError
