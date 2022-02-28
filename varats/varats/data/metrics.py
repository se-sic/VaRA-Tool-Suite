"""This module contains functions that calculate various metrics on data."""
import typing as tp

import numpy as np
import numpy.typing as npt
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
    dist_array: npt.NDArray[np.float64] = np.array(distribution)
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


def apply_tukeys_fence(
    data: pd.DataFrame, column: str, k: float
) -> pd.DataFrame:
    """
    Removes rows which are outliers in the given column using Tukey's fence.

    Tukey's fence defines all values to be outliers that are outside the range
    `[q1 - k * (q3 - q1), q3 + k * (q3 - q1)]`, i.e., values that are further
    than `k` times the inter-quartile range away from the first or third
    quartile.

    Common values for ``k``:
      - 2.2 (“Fine-Tuning Some Resistant Rules for Outlier Labeling”,
             Hoaglin and Iglewicz (1987))
      - 1.5 (outliers, “Exploratory Data Analysis”, John W. Tukey (1977))
      - 3.0 (far out outliers, “Exploratory Data Analysis”,
             John W. Tukey (1977))

    Args:
        data: data to remove outliers from
        column: column to use for outlier detection
        k: multiplicative factor on the inter-quartile-range

    Returns:
        the data without outliers
    """
    quartile_1 = data[column].quantile(0.25)
    quartile_3 = data[column].quantile(0.75)
    iqr = quartile_3 - quartile_1
    return tp.cast(
        pd.DataFrame, data.loc[(data[column] >= quartile_1 - k * iqr) &
                               (data[column] <= quartile_3 + k * iqr)]
    )
