"""Utility module for creating enhanced scatter plots."""

import typing as tp

import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt


def multivariate_grid(
    x_col: str,
    y_col: str,
    hue: str,
    data: pd.DataFrame,
    global_kde: bool = True,
    scatter_alpha: float = .5
) -> sns.JointGrid:
    """
    Make a seaborn JointPlot with additional global KDE plots.

    Code adapted from https://stackoverflow.com/a/55165689.

    Args:
        x_col: x variable name
        y_col: y variable name
        hue: hue variable name
        data: dataframe with the plot data
        global_kde: whether to include a kde for the sum of all data
        scatter_alpha: alpha value for the scatter plot
    """

    def colored_scatter(
        x_data: pd.Series,
        y_data: pd.Series,
        color: tp.Optional[str] = None
    ) -> tp.Callable[[tp.Any, tp.Any], None]:

        def scatter(*args: tp.Any, **kwargs: tp.Any) -> None:
            kwargs["x"] = x_data
            kwargs["y"] = y_data
            if color is not None:
                kwargs["c"] = color
            kwargs["alpha"] = scatter_alpha
            kwargs["s"] = 75
            ax = sns.scatterplot(*args, **kwargs)
            ax.xaxis.label.set_size(20)
            ax.yaxis.label.set_size(20)
            ax.tick_params(labelsize=15)

        return scatter

    min_x = data[x_col].min()
    max_x = data[x_col].max()
    range_x = max_x - min_x
    min_y = data[y_col].min()
    max_y = data[y_col].max()
    range_y = max_y - min_y

    grid = sns.JointGrid(
        x=x_col,
        y=y_col,
        data=data,
        xlim=(min_x - 0.05 * range_x, max_x + 0.05 * range_x),
        ylim=(min_y - 0.05 * range_y, max_y + 0.05 * range_y)
    )
    color = None
    legends = []
    grouped_data = data.groupby(hue)
    for name, df_group in grouped_data:
        legends.append(name)
        grid.plot_joint(
            colored_scatter(df_group[x_col], df_group[y_col], color)
        )
        sns.kdeplot(
            x=df_group[x_col].values, ax=grid.ax_marg_x, color=color, fill=True
        )
        sns.kdeplot(
            y=df_group[y_col].values, ax=grid.ax_marg_y, color=color, fill=True
        )
    if global_kde:
        sns.kdeplot(x=data[x_col].values, ax=grid.ax_marg_x, color='grey')
        sns.kdeplot(y=data[y_col].values, ax=grid.ax_marg_y, color='grey')
    if len(grouped_data) > 1:
        plt.legend(legends)

    return grid
