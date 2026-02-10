"""This module provides different sampling-method interface classes."""
import abc
import json
from collections.abc import Callable
from enum import Enum
from typing import Any, TYPE_CHECKING, TypeVar, TypeAlias, TypeGuard, cast

from varats.base.configuration import Configuration

if TYPE_CHECKING:
    import numpy as np


class SamplingMethodBase(abc.ABC):
    """
    Represents the sampling configuration added as a base class to all sampling
    methods.

    This class is designed to make the configuration of a sampling method
    persistable.
    """

    CONFIG_TYPE_NAME = 'sampling_method'

    _methods: dict[str, type['SamplingMethodBase']] = {}

    def __init__(self, **kwargs: Any) -> None:
        pass

    @classmethod
    def __init_subclass__(cls, *args: Any, **kwargs: Any) -> None:
        super().__init_subclass__(*args, **kwargs)
        cls._methods[cls.name()] = cls

    @classmethod
    def sampling_method_names(cls) -> list[str]:
        """
        Returns a list of all registered sampling method names.

        Returns: list of sampling method names
        """
        return list(cls._methods.keys())

    @classmethod
    def get_sampling_method_type(
        cls, sampling_method_name: str
    ) -> type['SamplingMethodBase']:
        """Maps the name of a `SamplingMethod` to the concrete type."""
        return cls._methods[sampling_method_name]

    @classmethod
    def sampling_method_types(cls) -> list[type['SamplingMethodBase']]:
        """
        Returns a list of all registered sampling method types.

        Returns: list of sampling method types
        """
        return list(cls._methods.values())

    @staticmethod
    def create_sampling_method(
        sampling_method_name: str, **kwargs: Any
    ) -> 'SamplingMethodBase':
        """
        Factory function for creating sampling methods.

        Args:
            sampling_method_name: name of the sampling method
            kwargs: additional arguments passed to the sampling method's
                    constructor and configuration function

        Returns: instantiated `SamplingMethod`
        """
        sampling_method_cls = SamplingMethodBase.get_sampling_method_type(
            sampling_method_name
        )
        sampling_method = sampling_method_cls(**kwargs)
        return sampling_method

    @staticmethod
    def create_sampling_method_from_config_str(
        config_str: str
    ) -> 'SamplingMethodBase':
        """
        Recreates a configured `SamplingMethod` from a config string.

        Args:
            config_str: SamplingMethod config as a string

        Returns: reinitialized `SamplingMethod`
        """
        loaded_dict = json.loads(config_str.replace('\'', "\""))
        sampling_method_name = loaded_dict.pop(
            SamplingMethodBase.CONFIG_TYPE_NAME
        )
        return SamplingMethodBase.create_sampling_method(
            sampling_method_name, **loaded_dict
        )

    @classmethod
    def name(cls) -> str:
        """Name of the sampling method."""
        return cls.__name__

    def dump_to_string(self) -> str:
        """
        Dumps the `SamplingConfiguration` to a string.

        This function is the inverse to
        `create_sampling_configuration_from_str` to dump a sampling
        configuration to be reparsed later.

        Returns: SamplingConfiguration as a string
        """
        partial_config = self._extend_config()
        partial_config[self.CONFIG_TYPE_NAME] = self.name()

        return str(partial_config)

    def _extend_config(self) -> dict[str, Any]:  # pylint: disable=R0201
        """
        Returns a configuration dict with config values from the subclass that
        should be persisted.

        Implementations in subclasses should always call
        `super()._extend_config()` first.
        """
        return {}


SampleType = TypeVar('SampleType')
SampleArray: TypeAlias = 'np.ndarray[tuple[int], np.dtype[np.float64]]'
SamplingMethod: TypeAlias = SamplingMethodBase


class NormalSamplingMethod(SamplingMethodBase):
    """Abstract base class for normal sampling methods that sample following a
    certain probability distribution."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def _extend_config(self) -> dict[str, Any]:
        """
        Returns a configuration dict with config values from the subclass that
        should be persisted.

        Implementations in subclasses should always call
        `super()._extend_config()` first.
        """
        partial_config = super()._extend_config()
        return partial_config

    @classmethod
    def get_normal_sampling_method_type(
        cls, sampling_method_name: str
    ) -> type['NormalSamplingMethod']:
        """Maps the name of a `NormalSamplingMethod` to the concrete type."""
        return cast(
            type[NormalSamplingMethod], cls._methods[sampling_method_name]
        )

    @classmethod
    def normal_sampling_method_types(cls) -> list[type['NormalSamplingMethod']]:
        """
        Returns a list of all registered normal sampling method types.

        Returns: list of `NormalSamplingMethod`s
        """
        return list(
            filter(
                NormalSamplingMethod.__is_normal_sampling_method,
                cls._methods.values()
            )
        )

    @staticmethod
    def __is_normal_sampling_method(
        sampling_method_type: type[SamplingMethodBase]
    ) -> TypeGuard[type['NormalSamplingMethod']]:
        return sampling_method_type is not NormalSamplingMethod and issubclass(
            sampling_method_type, NormalSamplingMethod
        )

    @abc.abstractmethod
    def gen_distribution_function(self) -> Callable[[int], SampleArray]:
        """
        Generate a distribution function for the specified sampling method.

        Returns:
            a callable that allows the caller to draw ``n`` numbers
            according to the selected distribution
        """

    def sample_n(self, data: list[SampleType],
                 num_samples: int) -> list[SampleType]:
        """
        Return a list of n unique samples. If the list to sample is smaller than
        the number of samples the full list is returned.

        Args:
            data: list to sample from
            num_samples: number of samples to choose

        Returns: list of sampled items
        """
        import numpy as np  # pylint: disable=import-outside-toplevel

        if num_samples >= len(data):
            return data

        probabilities = self.gen_distribution_function()(len(data))
        probabilities /= probabilities.sum()

        sampled_idxs = np.random.choice(
            len(data), num_samples, replace=False, p=probabilities
        )

        return [data[idx] for idx in sampled_idxs]


class UniformSamplingMethod(NormalSamplingMethod):
    """SampleMethod based on the uniform distribution."""

    def gen_distribution_function(self) -> Callable[[int], SampleArray]:
        """
        Generate a distribution function for the specified sampling method.

        Returns:
            a callable that allows the caller to draw ``n`` numbers
            according to the selected distribution
        """

        def uniform(num_samples: int) -> SampleArray:
            import numpy as np  # pylint: disable=import-outside-toplevel
            return np.asarray(np.random.uniform(0, 1.0, num_samples))

        return uniform


class HalfNormalSamplingMethod(NormalSamplingMethod):
    """SampleMethod based on a half-normal distribution."""

    def gen_distribution_function(self) -> Callable[[int], SampleArray]:
        """
        Generate a distribution function for the specified sampling method.

        Returns:
            a callable that allows the caller to draw ``n`` numbers
            according to the selected distribution
        """

        def halfnormal(num_samples: int) -> SampleArray:
            # pylint: disable=import-outside-toplevel
            from scipy.stats import halfnorm
            return np.asarray(halfnorm.rvs(scale=1, size=num_samples))

        return halfnormal


class EveryNSamplingMethod(SamplingMethodBase):
    """SampleMethod sampling every n-th revision."""

    def __init__(self, step: int, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.__step = step

    def _extend_config(self) -> dict[str, Any]:
        partial_config = super()._extend_config()
        partial_config["step"] = self.__step
        return partial_config

    def gen_distribution_function(self) -> Callable[[int], SampleArray]:
        """
        Generate a distribution function for the specified sampling method.

        Returns:
            a callable that allows the caller to draw ``n`` numbers
            according to the selected distribution
        """

        def every_nth(num_samples: int) -> SampleArray:
            import numpy as np  # pylint: disable=import-outside-toplevel
            return np.arange(
                0, num_samples * self.__step, self.__step, dtype=np.float64
            )

        return every_nth

    def sample_n(self, data: list[SampleType],
                 num_samples: int) -> list[SampleType]:
        """
        Return a list of n unique samples. If the list to sample is smaller than
        the number of samples the full list is returned.

        Args:
            data: list to sample from
            num_samples: number of samples to choose

        Returns: list of sampled items
        """
        end = min(num_samples * self.__step, len(data))
        return list(reversed(data))[0:end:self.__step]


class SamplingStrategy(abc.ABC):  # @Kalti: better name? Sampling heuristic?
    """A base class for all sampling strategies."""


class SampleN(SamplingStrategy):
    """Sample N, selects a random amount of `N` samples from the whole
    population."""

    def __init__(self, amount: int = 1) -> None:
        self.__amount = amount

    @property
    def amount(self) -> int:
        """
        Amount of options that should be sampled.

        >>> SampleN(42).amount
        42
        """
        return self.__amount


class SampleOptionWise(SamplingStrategy):
    """Option-wise sampling selects configurations such that it purposefully
    avoids interactions."""


class SamplePairWise(SamplingStrategy):
    """Pair-wise sampling, constructs a learning set that includes a minimal set
    of configurations, in which all two-way interactions are present and not
    confounded with other interactions."""


class SampleTripleWise(SamplingStrategy):
    """Triple-wise sampling, constructs a learning set that includes a minimal
    set of configurations, in which all three-way interactions are present and
    not confounded with other interactions."""


class Solver(Enum):
    """Represents the type of solver used in the background of the
    `SamplingMethod`."""

    NO_SOLVER = None
    Z3 = 1


class FeatureSamplingMethod(SamplingMethodBase):
    """Abstract base class for feature-sampling methods that sample
    configurations from a feature model based on different sampling
    strategies."""

    def __init__(
        self, solver: Solver = Solver.NO_SOLVER, **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        self.__solver = solver

    def _extend_config(self) -> dict[str, Any]:
        """
        Returns a configuration dict with config values from the subclass that
        should be persisted.

        Implementations in subclasses should always call
        `super()._extend_config()` first.
        """
        partial_config = super()._extend_config()
        partial_config["solver"] = self.__solver
        return partial_config

    @property
    def solver(self) -> Solver:
        return self.__solver

    @abc.abstractmethod
    def sample(
        self, feature_model: Any, partial_config: Configuration | None,
        strategy: SamplingStrategy | None
    ) -> list[Configuration]:
        """
        Sample a list of `Configurations` from a given `FeatureModel` according
        to a given strategy.

        Args:
            feature_model: to sample Configurations from
            partial_config: that already exists
            strategy: to sample the `Configuration`s

        Returns: list of `Configurations`
        """
        raise NotImplementedError
