"""This module contains functions that calculate various metrics on data."""
import typing as tp

import numpy as np
import numpy.typing as npt
import pandas as pd


def lorenz_curve(data: pd.Series) -> pd.Series:
    """
    Calculates the values for the lorenz curve of the data.

    For more information see online
    `lorenz curve <https://en.wikipedia.org/wiki/Lorenz_curve>`_.

    Args:
        data: sorted series to calculate the lorenz curve for

    Returns:
        the values of the lorenz curve as a series
    """
    scaled_prefix_sum = data.cumsum() / data.sum()
    return tp.cast(pd.Series, scaled_prefix_sum)


def gini_coefficient(distribution: pd.Series) -> float:
    """
    Calculates the Gini coefficient of the data.

    For more information see online
    `gini coefficient <https://en.wikipedia.org/wiki/Gini_coefficient>`_.

    Args:
        distribution: sorted series to calculate the Gini coefficient for

    Returns:
        the Gini coefficient for the data
    """
    dist_array: npt.NDArray[np.float64] = np.array(distribution)
    return 0.5 * float(
        ((np.abs(np.subtract.outer(dist_array, dist_array)).mean()) /
         np.mean(dist_array))
    )


def normalized_gini_coefficient(distribution: pd.Series) -> float:
    """
    Calculates the normalized Gini coefficient of the given data, , i.e.,

    ``gini(data) * (n / n - 1)`` where ``n`` is the length of the data.

    Args:
        distribution: sorted series to calculate the normalized Gini coefficient
                      for

    Returns:
        the normalized Gini coefficient for the data
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
    than `k` times the interquartile range away from the first or third
    quartile.

    Common values for ``k``:

    +-----+---------------------------------------------------------------+
    | 2.2 | (“Fine-Tuning Some Resistant Rules for Outlier Labeling”,     |
    |     |   Hoaglin and Iglewicz (1987))                                |
    +-----+---------------------------------------------------------------+
    | 1.5 | (outliers, “Exploratory Data Analysis”, John W. Tukey (1977)) |
    +-----+---------------------------------------------------------------+
    | 3.0 | (far out outliers, “Exploratory Data Analysis”,               |
    |     |  John W. Tukey (1977))                                        |
    +-----+---------------------------------------------------------------+

    Args:
        data: data to remove outliers from
        column: column to use for outlier detection
        k: multiplicative factor on the inter-quartile-range

    Returns:
        the data without outliers

    Test:
    >>> apply_tukeys_fence(pd.DataFrame({'foo': [1,1,2,2,10]})
    ...                    .rename_axis('cols', axis=1), 'foo', 3)
    cols  foo
    0       1
    1       1
    2       2
    3       2
    """
    quartile_1 = data[column].quantile(0.25)
    quartile_3 = data[column].quantile(0.75)
    iqr = quartile_3 - quartile_1
    return tp.cast(
        pd.DataFrame, data.loc[(data[column] >= quartile_1 - k * iqr) &
                               (data[column] <= quartile_3 + k * iqr)]
    )


def min_max_normalize(values: pd.Series) -> pd.Series:
    """
    Min-Max normalize a series.

    Args:
        values: the series to normalize

    Returns:
        the normalized series

    Test:
    >>> min_max_normalize(pd.Series([1,2,3]))
    0    0.0
    1    0.5
    2    1.0
    dtype: float64
    """
    max_value = values.max()
    min_value = values.min()
    return tp.cast(pd.Series, (values - min_value) / (max_value - min_value))


T = tp.TypeVar("T")


class ConfusionMatrix(tp.Generic[T]):
    """
    Helper class to automatically calculate classification results.

                        |  Predicted Positive (PP)  |  Predicted Negative (PN)
    --------------------|---------------------------|--------------------------
    Actual Positive (P) |  True Positive      (TP)  |  False Negative     (FN)
    Actual Negative (N) |  False Positive     (FP)  |  True Negative      (TN)

    Reference: https://en.wikipedia.org/wiki/Precision_and_recall
    """

    def __init__(
        self, actual_positive_values: tp.List[T],
        actual_negative_values: tp.List[T],
        predicted_positive_values: tp.List[T],
        predicted_negative_values: tp.List[T]
    ) -> None:
        self.__actual_positive_values = actual_positive_values
        self.__actual_negative_values = actual_negative_values
        self.__predicted_positive_values = predicted_positive_values
        self.__predicted_negative_values = predicted_negative_values

    ###################
    # Base metrics

    @property
    def P(self) -> int:  # pylint: disable=C0103
        return len(self.__actual_positive_values)

    @property
    def N(self) -> int:  # pylint: disable=C0103
        return len(self.__actual_negative_values)

    @property
    def PP(self) -> int:  # pylint: disable=C0103
        return len(self.__predicted_positive_values)

    @property
    def PN(self) -> int:  # pylint: disable=C0103
        return len(self.__predicted_negative_values)

    ###################
    # Combined metrics

    @property
    def TP(self) -> int:  # pylint: disable=C0103
        return len(self.getTPs())

    @property
    def TN(self) -> int:  # pylint: disable=C0103
        return len(self.getTNs())

    @property
    def FP(self) -> int:  # pylint: disable=C0103
        return self.PP - self.TP

    @property
    def FN(self) -> int:  # pylint: disable=C0103
        return self.PN - self.TN

    ###################
    # Combined values

    def getTPs(self) -> tp.Set[T]:  # pylint: disable=C0103
        return set(self.__actual_positive_values
                  ).intersection(self.__predicted_positive_values)

    def getTNs(self) -> tp.Set[T]:  # pylint: disable=C0103
        return set(self.__actual_negative_values
                  ).intersection(self.__predicted_negative_values)

    def getFPs(self) -> tp.Set[T]:  # pylint: disable=C0103
        return set(self.__predicted_positive_values
                  ).intersection(self.__actual_negative_values)

    def getFNs(self) -> tp.Set[T]:  # pylint: disable=C0103
        return set(self.__predicted_negative_values
                  ).intersection(self.__actual_positive_values)

    ###################
    # Interpretations

    def precision(self) -> float:
        """Positive predictive value (PPV)"""
        if self.PP == 0:
            return float('nan')

        return self.TP / self.PP

    def recall(self) -> float:
        """True positive rate (TPR)"""
        if self.P == 0:
            return float('nan')

        return self.TP / self.P

    def specificity(self) -> float:
        """True negative rate (TNR)"""
        if self.N == 0:
            return float('nan')

        return self.TN / self.N

    def accuracy(self) -> float:
        """Accuracy (ACC)"""
        if (self.P + self.N) == 0:
            return float('nan')

        return (self.TP + self.TN) / (self.P + self.N)

    def balanced_accuracy(self) -> float:
        """
        Balanced accuracy (BA)/(bACC)

        Balanced accuracy can serve as an overall performance metric for a
        model, whether or not the true labels are imbalanced in the data,
        assuming the cost of FN is the same as FP.
        """
        return (self.recall() + self.specificity()) / 2

    def f1_score(self) -> float:
        """In statistical analysis of binary classification, the F-score or
        F-measure is a measure of a test's accuracy."""
        numerator = 2 * self.TP
        denominator = 2 * self.TP + self.FP + self.FN
        if denominator == 0.0:
            return float('nan')

        return numerator / denominator

    ###################
    # python underscore methods
    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return f"""ConfM[TP={self.TP}, TN={self.TN}, FP={self.FP}, FN={self.FN}]
  ├─ Precision: {self.precision()}
  ├─ Recall:    {self.recall()}
  ├─ Accuracy:  {self.accuracy()}
  └─ F1_Score:  {self.f1_score()}
"""
