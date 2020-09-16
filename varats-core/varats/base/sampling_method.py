import abc
import typing as tp
from enum import Enum

import numpy as np
from scipy.stats import halfnorm


class SamplingMethod(Enum):

    uniform = 1
    half_norm = 2

    # TODO (sattlerf): refactor to correct base class

    def gen_distribution_function(self) -> tp.Callable[[int], np.ndarray]:
        """
        Generate a distribution function for the specified sampling method.

        Returns:
            a callable that allows the caller to draw ``n`` numbers
            according to the selected distribution
        """
        if self == SamplingMethod.uniform:

            def uniform(num_samples: int) -> np.ndarray:
                return tp.cast(
                    tp.List[float], np.random.uniform(0, 1.0, num_samples)
                )

            return uniform
        if self == SamplingMethod.half_norm:

            def halfnormal(num_samples: int) -> np.ndarray:
                return tp.cast(
                    tp.List[float], halfnorm.rvs(scale=1, size=num_samples)
                )

            return halfnormal

        raise Exception('Unsupported SamplingMethod')

    @abc.abstractproperty
    def get_name(self) -> str:  # TODO: rename to name after enum removal
        """Name of the sampling method."""
