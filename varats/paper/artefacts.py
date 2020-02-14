"""
Artifacts (e.g., plots) that can be generated for a paper config.
"""
import abc
import typing as tp
from abc import ABC
from enum import Enum
from pathlib import Path

from varats.data.version_header import VersionHeader
from varats.plots.plot import Plot
from varats.plots.plots import PlotRegistry
from varats.settings import CFG
from varats.utils.yaml_util import store_as_yaml, load_yaml


class Artefact(ABC):
    """
    An `Artefact` is a file that can be generated from the results produced
    by a paper config.
    Examples for artefacts are plots or result tables.
    
    Args:
        artefact_type: The type of this artefact. 
        name: The name of the artefact.
        output_path: The path where the file this artefact produces will be 
                     stored.
        
    """

    def __init__(self, artefact_type: 'ArtefactType', name: str,
                 output_path: Path) -> None:
        self.__artefact_type = artefact_type
        self.__name = name
        self.__output_path = output_path

    @property
    def artefact_type(self) -> 'ArtefactType':
        """
        The type of this artefact. 
        """
        return self.__artefact_type

    @property
    def name(self) -> str:
        """
        The name of this artefact
        """
        return self.__name

    @property
    def output_path(self) -> Path:
        """
        The output path of this artefact.
        """
        return Path(str(CFG['plots']['plot_dir'])) / self.__output_path

    def get_dict(self) -> tp.Dict[str, str]:
        """
        Construct a dict from this artefact for easy export to yaml.

        Subclasses should first call this function on `super()` and
        extend the returned dict with their own properties.

        Returns: A dict representation of this artefact.
        """
        return {
            'artefact_type': self.artefact_type.name,
            'name': self.name,
            'output_path': str(self.output_path)
        }

    @abc.abstractmethod
    def generate_artefact(self) -> None:
        """
        Generate the specified artefact.
        """


class PlotArtefact(Artefact):
    """
    An artefact defining a plot.
    
    Args:
        name: The name of the artefact.
        output_path: The path where the file this artefact produces will be 
                     stored.
        plot_type: The type of plot that will be generated.
        file_format: The file format of the generated plot.
        kwargs: Additional arguments that will be passed to the plot class.
    """

    def __init__(self,
                 name: str,
                 output_path: Path,
                 plot_type: str,
                 file_format: str,
                 **kwargs: tp.Any) -> None:
        super().__init__(ArtefactType.plot, name, output_path)
        self.__plot_type = plot_type
        self.__plot_type_class = PlotRegistry.get_class_for_plot_type(plot_type)
        self.__file_format = file_format
        self.__plot_kwargs = kwargs

    @property
    def plot_type(self) -> str:
        """
        The type of plot that will be generated.
        """
        return self.__plot_type

    @property
    def plot_type_class(self) -> tp.Type[Plot]:
        """
        The class associated with plot_type.
        """
        return self.__plot_type_class

    @property
    def file_format(self) -> str:
        """
        The file format of the generated plot.
        """
        return self.__file_format

    @property
    def plot_kwargs(self) -> tp.Any:
        """
        Additional arguments that will be passed to the plot_type_class.
        """
        return self.__plot_kwargs

    def get_dict(self) -> tp.Dict[str, str]:
        artefact_dict = super().get_dict()
        artefact_dict['plot_type'] = self.__plot_type
        artefact_dict['file_format'] = self.__file_format
        artefact_dict = {**self.plot_kwargs, **artefact_dict}
        return artefact_dict

    def generate_artefact(self) -> None:
        plot = self.plot_type_class(**self.plot_kwargs)
        plot.style = "ggplot"
        plot.save(self.file_format)


class ArtefactType(Enum):
    plot = PlotArtefact


class Artefacts:
    """
    A collection of `Artefact`s.
    """

    def __init__(self, artefacts: tp.Iterable[Artefact]) -> None:
        self.__artefacts = list(artefacts)

    @property
    def artefacts(self) -> tp.Iterable[Artefact]:
        """
        An iterator of the artefacts in this collection.
        """
        return self.__artefacts

    def add_artefact(self, artefact: Artefact) -> None:
        """
        Add an artefact to this collection of artefacts.

        Args:
            artefact: The artefact to add.
        """
        self.__artefacts.append(artefact)

    def __iter__(self) -> tp.Iterator[Artefact]:
        return self.__artefacts.__iter__()

    def get_dict(self) -> tp.Dict[str, tp.List[tp.Dict[str, str]]]:
        """
        Construct a dict from these artefacts for easy export to yaml.
        """
        return dict(
            artefacts=[artefact.get_dict() for artefact in self.artefacts])


def create_artefact(artefact_type: 'ArtefactType', name: str, output_path: Path,
                    **kwargs: tp.Any) -> Artefact:
    if artefact_type is ArtefactType.plot:
        plot_type = kwargs.pop('plot_type')
        file_format = kwargs.pop('file_format', 'png')
        return PlotArtefact(name, output_path, plot_type, file_format, **kwargs)


def load_artefacts_from_file(file_path: Path) -> Artefacts:
    """
    Load an artefacts file.

    Args:
        file_path: The path to the artefacts file.

    """
    documents = load_yaml(file_path)
    version_header = VersionHeader(next(documents))
    version_header.raise_if_not_type("Artefacts")
    version_header.raise_if_version_is_less_than(1)

    raw_artefacts = next(documents)
    artefacts: tp.List[Artefact] = []
    for raw_artefact in raw_artefacts.pop('artefacts'):
        name = raw_artefact.pop('name')
        output_path = raw_artefact.pop('output_path')
        artefact_type = ArtefactType[raw_artefact.pop('artefact_type')]
        artefacts.append(
            create_artefact(artefact_type, name, output_path, **raw_artefact))

    return Artefacts(artefacts)


def store_artefacts(artefacts: Artefacts, artefacts_location: Path) -> None:
    """
    Store artefacts to file in the specified paper_config.

    Args:
        artefacts: The artefacts to store.
        artefacts_location: The location for the artefacts file.
                            Can be either a path to a paper_config
                            or a direct path to an `artefacts.yaml` file.
    """
    if artefacts_location.suffix == '.yaml':
        __store_artefacts_to_file(artefacts, artefacts_location)
    else:
        __store_artefacts_to_file(artefacts,
                                  artefacts_location / 'artefacts.yaml')


# TODO: almost same as for case study -> refactor exporter
def __store_artefacts_to_file(artefacts: Artefacts, file_path: Path) -> None:
    """
    Store artefacts to file.
    """
    store_as_yaml(
        file_path,
        [VersionHeader.from_version_number('Artefacts', 1), artefacts])
