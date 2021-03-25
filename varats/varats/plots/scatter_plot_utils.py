import typing as tp

import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt


def multivariate_grid(
    x_col: str,
    y_col: str,
    hue: str,
    data: pd.DataFrame,
    scatter_alpha: float = .5
) -> None:
    """
    Make a seaborn JointPlot with additional global KDE plots.

    Code adapted from https://stackoverflow.com/a/55165689.

    Args:
        x_col: x variable name
        y_col: y variable name
        hue: hue variable name
        data: dataframe with the plot data
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
            sns.scatterplot(**kwargs)

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
        sns.kdeplot(x=df_group[x_col].values, ax=grid.ax_marg_x, color=color)
        sns.kdeplot(y=df_group[y_col].values, ax=grid.ax_marg_y, color=color)
    # Do also global kde:
    sns.kdeplot(x=data[x_col].values, ax=grid.ax_marg_x, color='grey')
    sns.kdeplot(y=data[y_col].values, ax=grid.ax_marg_y, color='grey')
    plt.legend(legends)

    plt.subplots_adjust(top=0.9)
    grid.fig.suptitle(f"{x_col} vs. {y_col}")
