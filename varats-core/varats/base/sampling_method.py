"""This module provides different sampling-method interface classes."""
import abc
import json
import typing as tp
from enum import Enum

import numpy as np
import numpy.typing as npt
from scipy.stats import halfnorm

from varats.base.configuration import Configuration

SamplingMethodSubType = tp.TypeVar('SamplingMethodSubType')


class SamplingMethodBase(tp.Generic[SamplingMethodSubType], abc.ABC):
    """
    Represents the sampling configuration added as a base class to all sampling
    methods.

    This class is designed to make the configuration of a sampling method
    persitable.
    """

    CONFIG_TYPE_NAME = 'sampling_method'

    _methods: tp.Dict[str, tp.Type[SamplingMethodSubType]] = {}

    @classmethod
    def __init_subclass__(cls, *args: tp.Any, **kwargs: tp.Any) -> None:
        super().__init_subclass__(*args, **kwargs)
        cls._methods[cls.name()] = cls

    @classmethod
    def sampling_method_names(cls) -> tp.List[str]:
        """
        Returns a list of all registered sampling method names.

        Returns: list of sampling method names
        """
        return list(cls._methods.keys())

    @classmethod
    def get_sampling_method_type(
        cls, sampling_method_name: str
    ) -> tp.Type[SamplingMethodSubType]:
        """Maps the name of a `SamplingMethod` to the concret type."""
        return cls._methods[sampling_method_name]

    @classmethod
    def sampling_method_types(cls) -> tp.List[tp.Type[SamplingMethodSubType]]:
        """
        Returns a list of all registered sampling method types.

        Returns: list of sampling method types
        """
        return list(cls._methods.values())

    @staticmethod
    def create_sampling_method_from_config_str(
        config_str: str
    ) -> SamplingMethodSubType:
        """
        Recreates a configured `SamplingMethod` from a config string.

        Args:
            config_str: SamplingMethod config as a string

        Returns: reinitialized `SamplingMethod`
        """
        loaded_dict = json.loads(config_str.replace('\'', "\""))

        sm_type: tp.Type[SamplingMethodSubType] = SamplingMethodBase[
            SamplingMethodSubType].get_sampling_method_type(
                loaded_dict[SamplingMethodBase.CONFIG_TYPE_NAME]
            )

        sm_obj: SamplingMethodSubType = sm_type()
        if not issubclass(type(sm_obj), SamplingMethodBase):
            raise AssertionError(
                "Sampling methods can only be created for classes which "
                "implement the SamplingMethodBase interface."
            )
        # sm_obj is always a subtype of SamplingMethodBase
        tp.cast(# pylint: disable=W0212
            'SamplingMethodBase[SamplingMethodSubType]', sm_obj
        )._configure_sampling_method(  # pylint: disable=W0212
            loaded_dict
        )
        return sm_obj

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

    def _extend_config(self) -> tp.Dict[str, tp.Any]:  # pylint: disable=R0201
        """
        Returns a configuration dict with config values from the sub class that
        should be persisted.

        Implementations in subclasses should always call
        `super()._extend_config()` first.
        """
        return {}

    def _configure_sampling_method(self, config: tp.Dict[str, str]) -> None:
        """
        Configures the `SamplingMethod` according to the provided config.

        Args:
            config: for the `SamplingMethod`

        Returns: configured `SamplingMethod`
        """


SamplingMethod = SamplingMethodBase[tp.Any]

SampleType = tp.TypeVar('SampleType')


class NormalSamplingMethod(SamplingMethodBase['NormalSamplingMethod']):
    """Abstract base class for normal sampling methods that sample following a
    certain probability distribution."""

    def __init__(self) -> None:
        pass

    def _extend_config(self) -> tp.Dict[str, tp.Any]:
        """
        Returns a configuration dict with config values from the sub class that
        should be persisted.

        Implementations in subclasses should always call
        `super()._extend_config()` first.
        """
        partial_config = super()._extend_config()
        return partial_config

    def _configure_sampling_method(self, config: tp.Dict[str, str]) -> None:
        """
        Configures the `SamplingMethod` according to the provided config.

        Args:
            config: for the `SamplingMethod`

        Returns: configured `SamplingMethod`
        """
        # We don't extend the config with own options, therefore, we don't have
        # to configure anything here.

    @classmethod
    def normal_sampling_method_types(
        cls
    ) -> tp.List[tp.Type['NormalSamplingMethod']]:
        """
        Returns a list of all registered normal sampling method types.

        Returns: list of `NormalSamplingMethod`s
        """
        return list(
            filter(
                lambda ty: ty is not NormalSamplingMethod and
                issubclass(ty, NormalSamplingMethod), cls._methods.values()
            )
        )

    @abc.abstractmethod
    def gen_distribution_function(
        self
    ) -> tp.Callable[[int], npt.NDArray[np.float64]]:
        """
        Generate a distribution function for the specified sampling method.

        Returns:
            a callable that allows the caller to draw ``n`` numbers
            according to the selected distribution
        """

    def sample_n(self, data: tp.List[SampleType],
                 num_samples: int) -> tp.List[SampleType]:
        """
        Return a list of n unique samples. If the list to sample is smaller than
        the number of samples the full list is returned.

        Args:
            data: list to sample from
            num_samples: number of samples to choose

        Returns: list of sampled items
        """
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

    def gen_distribution_function(
        self
    ) -> tp.Callable[[int], npt.NDArray[np.float64]]:
        """
        Generate a distribution function for the specified sampling method.

        Returns:
            a callable that allows the caller to draw ``n`` numbers
            according to the selected distribution
        """

        def uniform(num_samples: int) -> npt.NDArray[np.float64]:
            return np.random.uniform(0, 1.0, num_samples)

        return uniform


class HalfNormalSamplingMethod(NormalSamplingMethod):
    """SampleMethod based on a half-normal distribution."""

    def gen_distribution_function(
        self
    ) -> tp.Callable[[int], npt.NDArray[np.float64]]:
        """
        Generate a distribution function for the specified sampling method.

        Returns:
            a callable that allows the caller to draw ``n`` numbers
            according to the selected distribution
        """

        def halfnormal(num_samples: int) -> npt.NDArray[np.float64]:
            return tp.cast(
                npt.NDArray[np.float64],
                halfnorm.rvs(scale=1, size=num_samples)
            )

        return halfnormal


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


class FeatureSamplingMethod(SamplingMethodBase['FeatureSamplingMethod']):
    """Abstract base class for feature-sampling methods that sample
    configurations from a feature model based on different sampling
    strategies."""

    def __init__(self, solver: Solver = Solver.NO_SOLVER) -> None:
        self.__solver = solver

    def _extend_config(self) -> tp.Dict[str, tp.Any]:
        """
        Returns a configuration dict with config values from the sub class that
        should be persisted.

        Implementations in subclasses should always call
        `super()._extend_config()` first.
        """
        partial_config = super()._extend_config()
        partial_config["solver"] = self.__solver
        return partial_config

    def _configure_sampling_method(self, config: tp.Dict[str, str]) -> None:
        """
        Configures the `SamplingMethod` according to the provided config.

        Args:
            config: for the `SamplingMethod`

        Returns: configured `SamplingMethod`
        """
        # TODO (ChristianKaltenecker): add impl to initialize solver from
        # config + add way to persist solver type and solver configuration in
        # the config
        raise NotImplementedError

    @property
    def solver(self) -> Solver:
        return self.__solver

    @abc.abstractmethod
    def sample(
        self, feature_model: tp.Any, partial_config: tp.Optional[Configuration],
        strategy: tp.Optional[SamplingStrategy]
    ) -> tp.List[Configuration]:
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
