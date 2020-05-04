"""
This module contains functions that calculate various metrics on data.
"""
import numpy as np
import pandas as pd


def lorenz_curve(data: pd.Series) -> pd.Series:
    """
    Calculates the values for the
    `lorenz curve <https://en.wikipedia.org/wiki/Lorenz_curve>`_ of the data.

    Args:
        data: sorted series to calculate the lorenz curve for

    Returns:
        the values of the lorenz curve as a series
    """
    scaled_prefix_sum = data.cumsum() / data.sum()
    return scaled_prefix_sum


def gini_coefficient(lorenz_values: pd.Series) -> pd.Series:
    """
    Calculates the 
    `gini coefficient <https://en.wikipedia.org/wiki/Gini_coefficient>`_
    for a lorenz curve.

    Args:
        lorenz_values: the values of a lorenz curve as optained by 
                       :func:`calculate_lorenz_curve()`
                       
    Returns:
        the gini coefficient for the lorenz curve
    """
    return 0.5 * (
        (np.abs(np.subtract.outer(lorenz_values, lorenz_values)).mean()) /
        np.mean(lorenz_values))
