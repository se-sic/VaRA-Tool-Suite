"""
Module for drawing commit-data metrics plots.

- scatter-plot matrix
"""
import abc
import typing as tp

import matplotlib.axes as axes
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import pearsonr, spearmanr
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from varats.data.databases.blame_diff_metrics_database import (
    BlameDiffMetricsDatabase,
)
from varats.data.reports.commit_report import CommitMap
from varats.plots.plot import Plot
from varats.plots.plot_utils import align_yaxis, pad_axes


def annotate_correlation(
    x_values: tp.List[int],
    y_values: tp.List[int],
    ax: axes.SubplotBase = None,
    **kwargs: tp.Any
) -> None:
    """Plot the correlation coefficient in the top right hand corner of a
    plot."""
    ax = ax or plt.gca()
    pearson_rho, _ = pearsonr(x_values, y_values)
    ax.annotate(
        f'$\\mathit{{\\rho_p}}$ = {pearson_rho:.2f}',
        xy=(.6, .9),
        xycoords=ax.transAxes,
        fontsize="small"
    )

    spearman_rho, _ = spearmanr(x_values, y_values)
    ax.annotate(
        f'$\\mathit{{\\rho_s}}$ = {spearman_rho:.2f}',
        xy=(.6, .77),
        xycoords=ax.transAxes,
        fontsize="small"
    )


def logit_scatterplot(
    x_values: tp.List[int],
    y_values: tp.List[int],
    ax: axes.SubplotBase = None,
    **kwargs: tp.Any
) -> None:
    """Plot a scatterplot with clusters as hue and plot a logit that estimates
    the clusters."""
    ax = ax or plt.gca()

    data = pd.DataFrame({'x_values': x_values, 'y_values': y_values})
    # dychtiomize y_values to be able to use logistic regression
    data['target'] = _cluster_data_by_kmeans(data['y_values'])

    ax2 = ax.twinx()
    ax2.set_ylim(0, 1)
    ax2.yaxis.set_visible(False)
    # plot logit
    sns.regplot(
        x='x_values',
        y='target',
        data=data,
        scatter=False,
        ci=None,
        logistic=True,
        ax=ax2,
        color='black',
        line_kws={'alpha': 0.25}
    )
    # scatterplot with the two clusters as hue
    sns.scatterplot(x='x_values', y='y_values', hue='target', data=data, ax=ax)
    pad_axes(ax, 0.01, 0.01)
    pad_axes(ax2, 0.01, 0.01)
    align_yaxis(ax, 0, ax2, 0)


def _cluster_data_by_quantile(data: pd.Series, quantile: float) -> np.array:
    n_rows = len(data)
    quantile_border = quantile * n_rows

    def to_quantile_index(value: int) -> int:
        return 0 if value <= quantile_border else 1

    return np.array([to_quantile_index(x) for x in data])


def _cluster_data_by_kmeans(data: pd.Series) -> np.array:
    data2 = data.to_numpy(copy=True).reshape(-1, 1)
    stscaler = StandardScaler().fit(data2)
    data2 = stscaler.transform(data2)
    cluster = KMeans(
        n_clusters=2,
        init=np.array([[np.min(data2)], [np.max(data2)]]),
        n_init=1
    ).fit(data2)
    return cluster.labels_


def hist(
    x_values: tp.List[int],
    ax: axes.SubplotBase = None,
    **kwargs: tp.Any
) -> None:
    ax = ax or plt.gca()

    plt.hist(x_values)

    # hack to adjust the histogram axis to the off-diag plots' axes.
    ax2 = ax.twinx()
    ax2.set_ylim(0, 1)
    ax2.yaxis.set_visible(False)
    pad_axes(ax, pad_y=0.01)
    pad_axes(ax2, pad_y=0.01)
    align_yaxis(ax, 0, ax2, 0)


class BlameDiffCorrelationMatrix(Plot):
    """Draws a scatter-plot matrix for blame-data metrics, comparing the
    different independent and dependent variables."""

    NAME = "b_correlation_matrix"

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    @abc.abstractmethod
    def plot(self, view_mode: bool) -> None:
        """Plot the current plot to a file."""
        commit_map: CommitMap = self.plot_kwargs['get_cmap']()
        case_study = self.plot_kwargs.get('plot_case_study', None)
        project_name = self.plot_kwargs["project"]

        sns.set(style="ticks", color_codes=True)

        variables = [
            "churn", "num_interactions", "num_interacting_commits",
            "num_interacting_authors"
        ]

        df = BlameDiffMetricsDatabase.get_data_for_project(
            project_name, ["revision", *variables], commit_map, case_study
        )
        df.set_index('revision', inplace=True)
        df.drop(df[df.churn == 0].index, inplace=True)

        grid = sns.PairGrid(df, vars=variables)

        grid.map_diag(hist)
        grid.map_offdiag(logit_scatterplot)
        grid.map_offdiag(annotate_correlation)

    def show(self) -> None:
        """Show the current plot."""
        self.plot(True)
        plt.show()

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError
