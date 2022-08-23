"""Utility module for creating enhanced scatter plots."""

import typing as tp

import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt


def multivariate_grid(
    data: pd.DataFrame,
    x: str,
    y: str,
    hue: str,
    global_kde: bool = True,
    **kwargs: tp.Any
) -> sns.JointGrid:
    """
    Make a seaborn JointPlot with additional global KDE plots.

    Code adapted from https://stackoverflow.com/a/55165689.

    Args:
        data: dataframe with the plot data
        x: x variable name
        y: y variable name
        hue: hue variable name
        global_kde: whether to include a kde for the sum of all data
    """
    min_x = data[x].min()
    max_x = data[x].max()
    range_x = max(1, max_x - min_x)
    mid_x = (min_x + max_x) / 2.0
    min_y = data[y].min()
    max_y = data[y].max()
    range_y = max(1, max_y - min_y)
    mid_y = (min_y + max_y) / 2.0

    grid = sns.JointGrid(
        x=x,
        y=y,
        data=data,
        hue=hue,
        xlim=(mid_x - 0.55 * range_x, mid_x + 0.55 * range_x),
        ylim=(mid_y - 0.55 * range_y, mid_y + 0.55 * range_y)
    )

    legends = []
    grouped_data = data.groupby(hue)
    for name, df_group in grouped_data:
        legends.append(name)
        ax = sns.scatterplot(
            data=df_group, x=x, y=y, ax=grid.ax_joint, **kwargs
        )
        ax.xaxis.label.set_size(20)
        ax.yaxis.label.set_size(20)
        ax.tick_params(labelsize=15)
        sns.kdeplot(
            data=df_group,
            x=x,
            ax=grid.ax_marg_x,
            fill=True,
            warn_singular=False
        )
        sns.kdeplot(
            data=df_group,
            y=y,
            ax=grid.ax_marg_y,
            fill=True,
            warn_singular=False
        )
    if global_kde:
        sns.kdeplot(
            data=data,
            x=x,
            ax=grid.ax_marg_x,
            color='grey',
            warn_singular=False
        )
        sns.kdeplot(
            data=data,
            y=y,
            ax=grid.ax_marg_y,
            color='grey',
            warn_singular=False
        )
    if len(grouped_data) > 1:
        plt.legend(legends)

    return grid
