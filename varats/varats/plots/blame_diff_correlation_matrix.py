"""
Module for drawing commit-data metrics plots.

- scatter-plot matrix
"""
import logging
import typing as tp

import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
import pandas as pd
import seaborn as sns
from matplotlib import axes
from scipy.stats import pearsonr, spearmanr
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from varats.data.databases.blame_diff_metrics_database import (
    BlameDiffMetricsDatabase,
    BlameDiffMetrics,
)
from varats.mapping.commit_map import CommitMap, get_commit_map
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plot.plot_utils import align_yaxis, pad_axes
from varats.plot.plots import PlotGenerator
from varats.plots.scatter_plot_utils import multivariate_grid
from varats.ts_utils.cli_util import CLIOptionTy, make_cli_option
from varats.ts_utils.click_param_types import (
    EnumChoice,
    REQUIRE_MULTI_CASE_STUDY,
)
from varats.utils.git_util import FullCommitHash

LOG = logging.getLogger(__name__)

REQUIRE_X_METRIC: CLIOptionTy = make_cli_option(
    "--var-x",
    type=EnumChoice(BlameDiffMetrics, case_sensitive=False),
    required=True,
    help="The metric shown on the x-axis of the distribution comparison plot."
)

REQUIRE_Y_METRIC: CLIOptionTy = make_cli_option(
    "--var-y",
    type=EnumChoice(BlameDiffMetrics, case_sensitive=False),
    required=True,
    help="The metric shown on the y-axis of the distribution comparison plot."
)


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
    data.sort_values(by='y_values', inplace=True)
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
    sns.scatterplot(
        x='x_values',
        y='y_values',
        # https://github.com/mwaskom/seaborn/issues/2194
        hue=data['target'].tolist(),
        data=data,
        ax=ax
    )
    pad_axes(ax, 0.01, 0.01)
    pad_axes(ax2, 0.01, 0.01)
    align_yaxis(ax, 0, ax2, 0)


def _cluster_data_by_quantile(data: pd.Series,
                              quantile: float) -> npt.NDArray[np.int_]:
    n_rows = len(data)
    quantile_border = quantile * n_rows

    def to_quantile_index(value: int) -> int:
        return 0 if value <= quantile_border else 1

    return np.array([to_quantile_index(i) for i, _ in enumerate(data)])


def _cluster_data_by_kmeans(data: pd.Series) -> npt.NDArray[tp.Any]:
    data2 = data.to_numpy(copy=True).reshape(-1, 1)
    stscaler = StandardScaler().fit(data2)
    data2 = stscaler.transform(data2)
    cluster = KMeans(
        n_clusters=2,
        init=np.array([[np.min(data2)], [np.max(data2)]]),
        n_init=1
    ).fit(data2)
    return np.asarray(cluster.labels_)


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


def log_interesting_revisions(
    x_var: str,
    y_var: str,
    data: pd.DataFrame,
    threshold: float = 0.75,
    limit: int = 10
) -> None:
    """
    Log revisions with large discrepancy between two variables.

    Args:
        x_var: name of the x variable
        y_var: name of the y variable
        data:  the data
        threshold: revisions with ``y/x > threshold`` will be logged
        limit: maximum number of interesting revisions to log
    """
    x_col = data[x_var]
    y_col = data[y_var]
    fractions = y_col / x_col
    max_fraction = fractions.loc[fractions != np.inf].max()
    fractions.replace(np.inf, max_fraction, inplace=True)
    fractions.replace(np.nan, 0, inplace=True)

    data['fraction'] = fractions
    data = data.sort_values(by=['fraction', x_var, y_var], ascending=False)

    fraction_threshold = (fractions.max() - fractions.min()) * threshold
    interesting_cases = data[data['fraction'] > fraction_threshold]
    LOG.info(
        f"Found {len(interesting_cases)} interesting revisions "
        f"({x_var}, {y_var})"
    )
    for rev, item in list(interesting_cases.iterrows())[:limit]:
        LOG.info(f"  {rev} ({x_var}={item[x_var]}, {y_var}={item[y_var]})")


class BlameDiffCorrelationMatrix(Plot, plot_name="b_correlation_matrix"):
    """Draws a scatter-plot matrix for blame-data metrics, comparing the
    different independent and dependent variables."""

    def plot(self, view_mode: bool) -> None:
        """Plot the current plot to a file."""

        case_study: CaseStudy = self.plot_kwargs["case_study"]
        project_name: str = case_study.project_name
        commit_map: CommitMap = get_commit_map(project_name)

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

        if LOG.isEnabledFor(logging.INFO):
            for x_var in variables:
                for y_var in variables:
                    if x_var != y_var:
                        log_interesting_revisions(x_var, y_var, df.copy())

        grid = sns.PairGrid(df, vars=variables)

        grid.map_diag(_hist)
        grid.map_offdiag(logit_scatterplot)
        grid.map_offdiag(annotate_correlation)

        plt.subplots_adjust(top=0.9)
        fig_title_default = f"Correlation matrix - Project {project_name}"
        grid.fig.suptitle(self.plot_config.fig_title(fig_title_default))

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class BlameDiffCorrelationMatrixGenerator(
    PlotGenerator,
    generator_name="correlation-matrix-plot",
    options=[REQUIRE_MULTI_CASE_STUDY]
):
    """Generates correlation-matrix plot(s) for the selected case study(ies)."""

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")

        return [
            BlameDiffCorrelationMatrix(
                self.plot_config, case_study=cs, **self.plot_kwargs
            ) for cs in case_studies
        ]


class BlameDiffDistribution(Plot, plot_name="b_distribution_comparison"):
    """Draws a scatter-plot matrix for blame-data metrics, comparing the
    different independent and dependent variables."""

    def plot(self, view_mode: bool) -> None:
        """Plot the current plot to a file."""

        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_study"]
        var_x = self.plot_kwargs["var_x"].value
        var_y = self.plot_kwargs["var_y"].value

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
            return tp.cast(
                pd.Series, (values - min_value) / (max_value - min_value)
            )

        dataframes = []
        for case_study, df in data:
            df[var_x] = normalize(df[var_x])
            df[var_y] = normalize(df[var_y])
            df["project"] = case_study.project_name
            dataframes.append(df)

        sns.set(style="ticks", color_codes=True)

        df = pd.concat(dataframes)
        df.set_index('revision', inplace=True)

        if "churn" in df:
            df.drop(df[df.churn == 0].index, inplace=True)

        multivariate_grid(x_col=var_x, y_col=var_y, hue='project', data=df)

    def plot_file_name(self, filetype: str) -> str:
        """
        Get the file name this plot will be stored to when calling save.

        Args:
            filetype: the file type for the plot

        Returns:
            the file name the plot will be stored to
        """
        pc_name = get_loaded_paper_config().path.name
        var_x = self.plot_kwargs['var_x'].value
        var_y = self.plot_kwargs['var_y'].value
        return f"{pc_name}_{self.name}_{var_x}_vs_{var_y}.{filetype}"

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class BlameDiffDistributionGenerator(
    PlotGenerator,
    generator_name="distribution-comparison-plot",
    options=[REQUIRE_MULTI_CASE_STUDY, REQUIRE_X_METRIC, REQUIRE_Y_METRIC]
):
    """Generates a distribution-comparison plot for the selected case
    study(ies)."""

    def generate(self) -> tp.List[Plot]:
        return [BlameDiffDistribution(self.plot_config, **self.plot_kwargs)]
