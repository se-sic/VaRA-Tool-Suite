"""This module contains functions that calculate various metrics on data."""
import numpy as np
import pandas as pd


def lorenz_curve(data: pd.Series) -> pd.Series:
    """
    Calculates the values for the lorenz curve of the data.

    For more information see online `lorenz curve
    <https://en.wikipedia.org/wiki/Lorenz_curve>`_.

    Args:
        data: sorted series to calculate the lorenz curve for

    Returns:
        the values of the lorenz curve as a series
    """
    scaled_prefix_sum = data.cumsum() / data.sum()
    return scaled_prefix_sum


def gini_coefficient(distribution: pd.Series) -> float:
    """
    Calculates the gini coefficient of the data.

    For more information see online `gini coefficient
    <https://en.wikipedia.org/wiki/Gini_coefficient>`_.

    Args:
        distribution: sorted series to calculate the gini coefficient for

    Returns:
        the gini coefficient for the data
    """
    dist_array = np.array(distribution)
    return 0.5 * float(
        ((np.abs(np.subtract.outer(dist_array, dist_array)).mean()) /
         np.mean(dist_array))
    )


def normalized_gini_coefficient(distribution: pd.Series) -> float:
    """
    Calculates the normalized gini coefficient of the given data, , i.e.,

    ``gini(data) * (n / n - 1)`` where ``n`` is the length of the data.

    Args:
        distribution: sorted series to calculate the normalized gini coefficient
                      for

    Returns:
        the normalized gini coefficient for the data
    """
    n = float(len(distribution))
    if n <= 1:
        return gini_coefficient(distribution)

    return gini_coefficient(distribution) * (n / (n - 1.0))
