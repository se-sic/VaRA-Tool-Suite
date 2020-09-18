import abc
import typing as tp
from enum import Enum

import numpy as np
from scipy.stats import halfnorm


class SamplingFoo(Enum):
    amount = 1,  ## amount = 42
    option_wise = 2,
    pair_wise = 3,
    tripe_wise = 4

    def extra_value(self) -> int:
        pass


class Solver(Enum):
    NoSolver = 0,
    Z3 = 1


class SamplingConfiguration():

    def dump_sampling_method(self) -> str:
        partial_config = self._extend_config()
        partial_config['solver'] = "mysolver"

        return "flaten(partial_config)"

    @abc.abstractmethod
    def _extend_config(self) -> tp.Dict[str, tp.Any]:
        pass

    @abc.abstractclassmethod
    def configure_sampling_method(
        cls, config_string: str
    ) -> 'SamplingMethod':  #TODO: type system
        pass


class SamplingMethod(SamplingConfiguration, Enum):

    uniform = 1
    half_norm = 2

    # TODO (sattlerf): refactor to correct base class

    def __init__(self, solver: Solver = Solver.NoSolver) -> None:
        self.__solver = solver

    @property
    def solver(self) -> Solver:
        return self.__solver

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

    # TODO: needs more specification
    #@abc.abstractmethod
    #def get_samples(
    #    feature_model, partial_config: tp.Optional['Configuration'],
    #    amount: tp.Optional[SamplingFoo]
    #) -> tp.List['Configuration']:
    #    """
    #    """


class FeatureSamplingMethod(SamplingConfiguration):
    pass


## example method
#class BandB(SamplingMethod):
#
#    def __init__(self, param1, param2):
#        pass
#        #self.__param = vara_cfg()["sampling"]["bandb"]["bb_value"]
#
#    #@classmethod
#    #def create_bandb_sampler(cls, param1: tp.Optional[int] = None):
#    #    if param1 is None:
#    #        set_param1 = vara_cfg()["sampling"]["bandb"]["bb_value"]
#
#    return BandB(param1 if param1 else set_param1, "foo")
