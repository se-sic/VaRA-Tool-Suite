"""
This module allows to attach :class:`artefact definitions<Artefact>` to a.

:class:`paper config<varats.paper_mgmt.paper_config>`. This way, the artefacts,
like :class:`plots<PlotArtefact>` or result tables, can be generated from
result files automatically.

Typically, a paper config has a file ``artefacts.yaml`` that manages artefact
definitions.
"""
import abc
import logging
import typing as tp
from abc import ABC
from enum import Enum
from pathlib import Path

from varats.base.version_header import VersionHeader
from varats.plot.plot import Plot
from varats.plot.plots import PlotRegistry, build_plots
from varats.table.table import TableFormat, Table
from varats.table.tables import TableRegistry, build_tables
from varats.utils.settings import vara_cfg
from varats.utils.yaml_util import load_yaml, store_as_yaml

LOG = logging.getLogger(__name__)


class Artefact(ABC):
    """
    An ``Artefact`` contains all information that is necessary to generate a
    certain artefact. Subclasses of this class specify concrete artefact types,
    like :class:`plots<PlotArtefact>`, that require additional attributes.

    Args:
        artefact_type: The :class:`type<ArtefactType>` of this artefact.
        name: The name of this artefact.
        output_path: The output path for this artefact.
    """

    def __init__(
        self, artefact_type: 'ArtefactType', name: str, output_path: Path
    ) -> None:
        self.__artefact_type = artefact_type
        self.__name = name
        self.__output_path = output_path

    @property
    def artefact_type(self) -> 'ArtefactType':
        """The :class:`type<ArtefactType>` of this artefact."""
        return self.__artefact_type

    @property
    def name(self) -> str:
        """
        The name of this artefact.

        This uniquely identifies an artefact in an
        :class:`Artefacts` collection.
        """
        return self.__name

    @property
    def output_path(self) -> Path:
        """
        The output path for this artefact.

        The output path is relative to the directory specified as
        ``artefacts.artefacts_dir`` in the current varats config.
        """
        return Path(str(vara_cfg()['artefacts']['artefacts_dir'])) / Path(
            str(vara_cfg()['paper_config']['current_config'])
        ) / self.__output_path

    def get_dict(self) -> tp.Dict[str, tp.Union[str, int]]:
        """
        Construct a dict from this artefact for easy export to yaml.

        Subclasses should first call this function on ``super()`` and then
        extend the returned dict with their own properties.

        Returns:
            A dict representation of this artefact.
        """
        return {
            'artefact_type': self.__artefact_type.name,
            'artefact_type_version': self.__artefact_type.value[1],
            'name': self.__name,
            'output_path': str(self.__output_path)
        }

    @abc.abstractmethod
    def generate_artefact(self) -> None:
        """Generate the specified artefact."""


class PlotArtefact(Artefact):
    """
    An artefact defining a :class:`plot<varats.plot.plot.Plot>`.

    Args:
        name: The name of this artefact.
        output_path: the path where the plot this artefact produces will be
                     stored
        plot_type: the
                    :attr:`type of plot<varats.plot.plots.PlotRegistry.plots>`
                    that will be generated
        file_format: the file format of the generated plot
        kwargs: additional arguments that will be passed to the plot class
    """

    def __init__(
        self, name: str, output_path: Path, plot_type: str, file_format: str,
        **kwargs: tp.Any
    ) -> None:
        super().__init__(ArtefactType.PLOT, name, output_path)
        self.__plot_type = plot_type
        self.__plot_type_class = PlotRegistry.get_class_for_plot_type(plot_type)
        self.__file_format = file_format
        self.__plot_kwargs = kwargs

    @property
    def plot_type(self) -> str:
        """The :attr:`type of plot<varats.plot.plots.PlotRegistry.plots>` that
        will be generated."""
        return self.__plot_type

    @property
    def plot_type_class(self) -> tp.Type[Plot]:
        """The class associated with :func:`plot_type`."""
        return self.__plot_type_class

    @property
    def file_format(self) -> str:
        """The file format of the generated plot."""
        return self.__file_format

    @property
    def plot_kwargs(self) -> tp.Any:
        """Additional arguments that will be passed to the plot_type_class."""
        return self.__plot_kwargs

    def get_dict(self) -> tp.Dict[str, tp.Union[str, int]]:
        artefact_dict = super().get_dict()
        artefact_dict['plot_type'] = self.__plot_type
        artefact_dict['file_format'] = self.__file_format
        artefact_dict = {**self.__plot_kwargs, **artefact_dict}
        return artefact_dict

    def generate_artefact(self) -> None:
        """Generate the specified plot."""
        if not self.output_path.exists():
            self.output_path.mkdir(parents=True)

        build_plots(
            plot_type=self.plot_type,
            result_output=self.output_path,
            file_format=self.file_format,
            **self.__plot_kwargs
        )


class TableArtefact(Artefact):
    """
    An artefact defining a :class:`table<varats.tables.table.Table>`.

    Args:
        name: The name of this artefact.
        output_path: the path where the table this artefact produces will be
                     stored
        table_type: the :attr:`type of table
                    <varats.tables.tables.TableRegistry.tables>`
                    that will be generated
        table_format: the format of the generated table
        kwargs: additional arguments that will be passed to the table class
    """

    def __init__(
        self, name: str, output_path: Path, table_type: str,
        table_format: TableFormat, **kwargs: tp.Any
    ) -> None:
        super().__init__(ArtefactType.TABLE, name, output_path)
        self.__table_type = table_type
        self.__table_type_class = TableRegistry.get_class_for_table_type(
            table_type
        )
        self.__table_format = table_format
        self.__table_kwargs = kwargs

    @property
    def table_type(self) -> str:
        """The :attr:`type of table<varats.table.tables.TableRegistry.plots>`
        that will be generated."""
        return self.__table_type

    @property
    def table_type_class(self) -> tp.Type[Table]:
        """The class associated with :func:`table_type`."""
        return self.__table_type_class

    @property
    def file_format(self) -> TableFormat:
        """The file format of the generated table."""
        return self.__table_format

    @property
    def table_kwargs(self) -> tp.Any:
        """Additional arguments that will be passed to the table_type_class."""
        return self.__table_kwargs

    def get_dict(self) -> tp.Dict[str, tp.Union[str, int]]:
        artefact_dict = super().get_dict()
        artefact_dict['table_type'] = self.__table_type
        artefact_dict['table_format'] = self.__table_format.name
        artefact_dict = {**self.__table_kwargs, **artefact_dict}
        return artefact_dict

    def generate_artefact(self) -> None:
        """Generate the specified table."""
        if not self.output_path.exists():
            self.output_path.mkdir(parents=True)

        build_tables(
            table_type=self.table_type,
            result_output=self.output_path,
            file_format=self.file_format,
            **self.table_kwargs
        )


class ArtefactType(Enum):
    """
    Enum for the different artefact types.

    The name is used in the ``artefacts.yaml`` to identify what kind of artefact
    is described. The values are tuples ``(artefact_class, version)`` consisting
    of the class responsible for that kind of artefact and a version number to
    allow evolution of artefacts.
    """
    value: tp.Tuple[Artefact, int]  # pylint: disable=invalid-name

    PLOT = (PlotArtefact, 1)
    TABLE = (TableArtefact, 1)


class Artefacts:
    r"""
    A collection of :class:`Artefact`\ s.
    """

    def __init__(self, artefacts: tp.Iterable[Artefact]) -> None:
        self.__artefacts = {artefact.name: artefact for artefact in artefacts}

    @property
    def artefacts(self) -> tp.Iterable[Artefact]:
        r"""
        An iterator of the :class:`Artefact`\ s in this collection.
        """
        return self.__artefacts.values()

    def get_artefact(self, name: str) -> tp.Optional[Artefact]:
        """
        Lookup an artefact by its name.

        Args:
            name: the name of the artefact to retrieve

        Returns:
            the artefact with the name ``name`` if available, else ``None``
        """
        return self.__artefacts.get(name)

    def add_artefact(self, artefact: Artefact) -> None:
        """
        Add an :class:`Artefact` to this collection.

        If there already exists an artefact with the same name it is overridden.

        Args:
            artefact: the artefact to add
        """
        self.__artefacts[artefact.name] = artefact

    def __iter__(self) -> tp.Iterator[Artefact]:
        return self.__artefacts.values().__iter__()

    def get_dict(
        self
    ) -> tp.Dict[str, tp.List[tp.Dict[str, tp.Union[str, int]]]]:
        """Construct a dict from these artefacts for easy export to yaml."""
        return dict(
            artefacts=[artefact.get_dict() for artefact in self.artefacts]
        )


def create_artefact(
    artefact_type: 'ArtefactType', name: str, output_path: Path,
    **kwargs: tp.Any
) -> Artefact:
    """
    Create a new :class:`Artefact` from the provided parameters.

    Args:
        artefact_type: the :class:`type<ArtefactType>` for the artefact
        name: the name of the artefact
        output_path: the output path for the artefact
        **kwargs: additional arguments that are passed to the class selected by
                  ``artefact_type``

    Returns:
        the created artefact
    """
    if artefact_type is ArtefactType.PLOT:
        plot_type = kwargs.pop('plot_type')
        file_format = kwargs.pop('file_format', 'png')
        return PlotArtefact(name, output_path, plot_type, file_format, **kwargs)
    if artefact_type is ArtefactType.TABLE:
        table_type = kwargs.pop('table_type')
        table_format = TableFormat[kwargs.pop('file_format', 'latex_booktabs')]
        return TableArtefact(
            name, output_path, table_type, table_format, **kwargs
        )

    raise AssertionError(
        f"Missing create function for artefact type {artefact_type}"
    )


def load_artefacts_from_file(file_path: Path) -> Artefacts:
    """
    Load an artefacts file.

    Args:
        file_path: the path to the artefacts file

    Returns:
        the artefacts created from the given file
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
        artefact_type = ArtefactType[raw_artefact.pop('artefact_type').upper()]
        artefact_type_version = raw_artefact.pop('artefact_type_version')
        if artefact_type_version < artefact_type.value[1]:
            LOG.warning(
                f"artefact {name} uses an old version of artefact "
                f"type {artefact_type.name}."
            )
        artefacts.append(
            create_artefact(artefact_type, name, output_path, **raw_artefact)
        )

    return Artefacts(artefacts)


def store_artefacts(artefacts: Artefacts, artefacts_location: Path) -> None:
    """
    Store artefacts to file in the specified paper_config.

    Args:
        artefacts: the artefacts to store
        artefacts_location: the location for the artefacts file.
                            Can be either a path to a paper_config
                            or a direct path to an `artefacts.yaml` file.
    """
    if artefacts_location.suffix == '.yaml':
        __store_artefacts_to_file(artefacts, artefacts_location)
    else:
        __store_artefacts_to_file(
            artefacts, artefacts_location / 'artefacts.yaml'
        )


def __store_artefacts_to_file(artefacts: Artefacts, file_path: Path) -> None:
    """Store artefacts to file."""
    store_as_yaml(
        file_path,
        [VersionHeader.from_version_number('Artefacts', 1), artefacts]
    )


def filter_plot_artefacts(
    artefacts: tp.Iterable[Artefact]
) -> tp.Iterable[PlotArtefact]:
    """
    Filter all plot artefacts from a list of artefacts.

    Args:
        artefacts: the artefacts to filter

    Returns:
        all plot artefacts
    """
    return [
        tp.cast(PlotArtefact, artefact)
        for artefact in artefacts
        if artefact.artefact_type == ArtefactType.PLOT
    ]


def filter_table_artefacts(
    artefacts: tp.Iterable[Artefact]
) -> tp.Iterable[TableArtefact]:
    """
    Filter all table artefacts from a list of artefacts.

    Args:
        artefacts: the artefacts to filter

    Returns:
        all table artefacts
    """
    return [
        tp.cast(TableArtefact, artefact)
        for artefact in artefacts
        if artefact.artefact_type == ArtefactType.TABLE
    ]
