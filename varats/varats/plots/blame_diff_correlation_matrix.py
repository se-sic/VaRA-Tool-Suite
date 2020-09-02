"""
Module for drawing commit-data metrics plots.

- scatter-plot matrix
"""
import abc
import typing as tp
from pathlib import Path

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
from varats.paper.paper_config import get_loaded_paper_config
from varats.plots.plot import Plot, PlotDataEmpty
from varats.plots.plot_utils import align_yaxis, pad_axes
from varats.tools.commit_map import get_commit_map


def annotate_correlation(
    x_values: tp.List[int],
    y_values: tp.List[int],
    ax: axes.SubplotBase = None,
    # pylint: disable=unused-argument
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
    # pylint: disable=unused-argument
    **kwargs: tp.Any
) -> None:
    """Plot a scatterplot with clusters as hue and plot a logit that estimates
    the clusters."""
    ax = ax or plt.gca()

    data = pd.DataFrame({'x_values': x_values, 'y_values': y_values})
    # dychotomize y_values to be able to use logistic regression
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


def _hist(
    x_values: tp.List[int],
    ax: axes.SubplotBase = None,
    # pylint: disable=unused-argument
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
            project_name, ["revision", "time_id", *variables], commit_map,
            case_study
        )
        df.set_index('revision', inplace=True)
        df.drop(df[df.churn == 0].index, inplace=True)
        if df.empty or len(df.index) < 2:
            raise PlotDataEmpty
        df.sort_values(by=['time_id'], inplace=True)

        grid = sns.PairGrid(df, vars=variables)

        grid.map_diag(_hist)
        grid.map_offdiag(logit_scatterplot)
        grid.map_offdiag(annotate_correlation)

        plt.subplots_adjust(top=0.9)
        grid.fig.suptitle(
            str("Correlation Matrix") +
            f' - Project {self.plot_kwargs["project"]}'
        )

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError


# adapted from https://stackoverflow.com/a/55165689
def _multivariate_grid(
    x_col: str,
    y_col: str,
    hue: str,
    data: pd.DataFrame,
    scatter_alpha: float = .5
) -> None:

    def colored_scatter(
        x_data: pd.Series,
        y_data: pd.Series,
        color: tp.Optional[str] = None
    ) -> tp.Callable[[tp.Any, tp.Any], None]:

        def scatter(*args: tp.Any, **kwargs: tp.Any) -> None:
            args = (x_data, y_data)
            if color is not None:
                kwargs['c'] = color
            kwargs['alpha'] = scatter_alpha
            sns.scatterplot(*args, **kwargs)

        return scatter

    grid = sns.JointGrid(
        x=x_col, y=y_col, data=data, xlim=(-0.05, 1.05), ylim=(-0.05, 1.05)
    )
    color = None
    legends = []
    for name, df_group in data.groupby(hue):
        legends.append(name)
        grid.plot_joint(
            colored_scatter(df_group[x_col], df_group[y_col], color)
        )
        sns.kdeplot(df_group[x_col].values, ax=grid.ax_marg_x, color=color)
        sns.kdeplot(
            df_group[y_col].values,
            ax=grid.ax_marg_y,
            color=color,
            vertical=True
        )
    # Do also global kde:
    sns.kdeplot(data[x_col].values, ax=grid.ax_marg_x, color='grey')
    sns.kdeplot(
        data[y_col].values, ax=grid.ax_marg_y, color='grey', vertical=True
    )
    plt.legend(legends)

    plt.subplots_adjust(top=0.9)
    grid.fig.suptitle(f"{x_col} vs. {y_col}")


class BlameDiffDistribution(Plot):
    """Draws a scatter-plot matrix for blame-data metrics, comparing the
    different independent and dependent variables."""

    NAME = "b_distribution_comparison"

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    @abc.abstractmethod
    def plot(self, view_mode: bool) -> None:
        """Plot the current plot to a file."""
        if "project" not in self.plot_kwargs:
            case_studies = get_loaded_paper_config().get_all_case_studies()
        else:
            if "plot_case_study" in self.plot_kwargs:
                case_studies = [self.plot_kwargs["plot_case_study"]]
            else:
                case_studies = get_loaded_paper_config().get_case_studies(
                    self.plot_kwargs["project"]
                )

        var_x = self.plot_kwargs["var_x"]
        var_y = self.plot_kwargs["var_y"]

        data = [(
            case_study,
            BlameDiffMetricsDatabase.get_data_for_project(
                case_study.project_name, ["revision", var_x, var_y],
                get_commit_map(case_study.project_name), case_study
            )
        ) for case_study in case_studies]

        def normalize(values: pd.Series) -> pd.Series:
            max_value = values.max()
            min_value = values.min()
            return (values - min_value) / (max_value - min_value)

        dataframes = []
        for case_study, df in data:
            df[var_x] = normalize(df[var_x])
            df[var_y] = normalize(df[var_y])
            df["project"] = case_study.project_name
            dataframes.append(df)

        sns.set(style="ticks", color_codes=True)

        df = pd.concat(dataframes)
        df.set_index('revision', inplace=True)
        df.drop(df[df.churn == 0].index, inplace=True)

        _multivariate_grid(
            x_col=var_x,
            y_col=var_y,
            hue='project',
            data=df,
        )

    def save(
        self, path: tp.Optional[Path] = None, filetype: str = 'svg'
    ) -> None:
        """
        Save the current plot to a file.

        Args:
            path: The path where the file is stored (excluding the file name).
            filetype: The file type of the plot.
        """
        self.plot(False)

        if path is None:
            plot_dir = Path(self.plot_kwargs["plot_dir"])
        else:
            plot_dir = path
        pc_name = get_loaded_paper_config().path.name

        # TODO (se-passau/VaRA#545): refactor dpi into plot_config. see.
        plt.savefig(
            plot_dir / f"{pc_name}_{self.name}_{self.plot_kwargs['var_x']}_vs_"
            f"{self.plot_kwargs['var_y']}.{filetype}",
            dpi=1200,
            format=filetype
        )
        plt.close()

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError
