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
from pathlib import Path

from varats.base.version_header import VersionHeader
from varats.utils.settings import vara_cfg
from varats.utils.yaml_util import load_yaml, store_as_yaml

if tp.TYPE_CHECKING:
    import varats.paper.case_study as cs  # pylint: disable=unused-import

LOG = logging.getLogger(__name__)


class ArtefactFileInfo():
    """Class containing metadata about a file generated by an artefact."""

    def __init__(
        self, file_name: str, case_study: tp.Optional['cs.CaseStudy'] = None
    ):
        self.__file_name = file_name
        self.__case_study = case_study

    @property
    def file_name(self) -> str:
        """The name of the generated file."""
        return self.__file_name

    @property
    def case_study(self) -> tp.Optional['cs.CaseStudy']:
        """The used case study if available."""
        return self.__case_study


class Artefact(ABC):
    """
    An ``Artefact`` contains all information that is necessary to generate a
    certain artefact. Subclasses of this class specify concrete artefact types,
    like :class:`plots<PlotArtefact>`, that require additional attributes.

    Args:
        name: name of this artefact
        output_dir: output dir relative to config value
                    'artefacts/artefacts_dir'
    """

    ARTEFACT_TYPE = "Artefact"
    ARTEFACT_TYPE_VERSION = 0
    ARTEFACT_TYPES: tp.Dict[str, tp.Type['Artefact']] = {}

    def __init__(self, name: str, output_dir: Path) -> None:
        self.__name = name
        self.__output_dir = output_dir

    @classmethod
    def __init_subclass__(
        cls, artefact_type: str, artefact_type_version: int, **kwargs: tp.Any
    ) -> None:
        """Register Artefact implementations."""
        # mypy does not yet fully understand __init_subclass__()
        # https://github.com/python/mypy/issues/4660
        super().__init_subclass__(**kwargs)  # type: ignore
        cls.ARTEFACT_TYPE = artefact_type
        cls.ARTEFACT_TYPE_VERSION = artefact_type_version
        cls.ARTEFACT_TYPES[cls.ARTEFACT_TYPE] = cls

    @staticmethod
    def base_output_dir() -> Path:
        """Base output dir for artefacts."""
        return Path(str(vara_cfg()['artefacts']['artefacts_dir'])
                   ) / Path(str(vara_cfg()['paper_config']['current_config']))

    @property
    def name(self) -> str:
        """
        The name of this artefact.

        This uniquely identifies an artefact in an
        :class:`Artefacts` collection.
        """
        return self.__name

    @property
    def output_dir(self) -> Path:
        """Absolute path to the artefact's output directory."""
        return Path(str(vara_cfg()['artefacts']['artefacts_dir'])) / Path(
            str(vara_cfg()['paper_config']['current_config'])
        ) / self.__output_dir

    def get_dict(self) -> tp.Dict[str, tp.Any]:
        """
        Construct a dict from this artefact for easy export to yaml.

        Subclasses should first call this function on ``super()`` and then
        extend the returned dict with their own properties.

        Returns:
            A dict representation of this artefact.
        """
        return {
            'artefact_type': self.ARTEFACT_TYPE,
            'artefact_type_version': self.ARTEFACT_TYPE_VERSION,
            'name': self.__name,
            'output_dir': str(self.__output_dir)
        }

    @staticmethod
    @abc.abstractmethod
    def create_artefact(
        name: str, output_dir: Path, **kwargs: tp.Any
    ) -> 'Artefact':
        """
        Instantiate an artefact from its dict representation.

        Args:
            name: name of this artefact
            output_dir: output dir relative to config value
                        'artefacts/artefacts_dir'
            **kwargs: artefact-specific arguments

        Returns:
            an instantiated artefact
        """

    @abc.abstractmethod
    def generate_artefact(self) -> None:
        """Generate the specified artefact."""

    @abc.abstractmethod
    def get_artefact_file_infos(self) -> tp.List[ArtefactFileInfo]:
        """Returns a list of file meta-date generated by this artefact."""


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


class ArtefactException(Exception):
    """Base class for artefact related exceptions."""


class UnknownArtefactType(Exception):
    """Thrown if an unknown artefact type is encountered."""


class OutdatedArtefactVersion(Exception):
    """Thrown if an artefact uses an outdated format."""


ARTEFACTS_FILE_VERSION = 2


def create_artefact(
    artefact_type_name: str, name: str, output_dir: Path, **kwargs: tp.Any
) -> Artefact:
    """
    Create a new :class:`Artefact` from the provided parameters.

    Args:
        artefact_type_name: the name of the artefact type for the artefact
        name: name of the artefact
        output_dir: output dir relative to config value
                    'artefacts/artefacts_dir'
        **kwargs: artefact-specific arguments

    Returns:
        the created artefact
    """
    artefact_type = Artefact.ARTEFACT_TYPES.get(artefact_type_name, None)
    if not artefact_type:
        raise UnknownArtefactType(
            f"Unknown artefact type '{artefact_type_name}'"
        )

    artefact_type_version = kwargs.pop(
        'artefact_type_version', artefact_type.ARTEFACT_TYPE_VERSION
    )
    if artefact_type_version < artefact_type.ARTEFACT_TYPE_VERSION:
        raise OutdatedArtefactVersion()

    return artefact_type.create_artefact(name, output_dir, **kwargs)


def load_artefacts_from_file(file_path: Path) -> Artefacts:
    """
    Load an artefacts file.

    Args:
        file_path: path to the artefacts file

    Returns:
        the artefacts created from the given file
    """
    documents = load_yaml(file_path)
    version_header = VersionHeader(next(documents))
    version_header.raise_if_not_type("Artefacts")
    version_header.raise_if_version_is_less_than(ARTEFACTS_FILE_VERSION)

    raw_artefacts = next(documents)
    artefacts: tp.List[Artefact] = []
    for raw_artefact in raw_artefacts.pop('artefacts'):
        artefact_type_name = raw_artefact.pop('artefact_type')
        name = raw_artefact.pop('name')
        output_dir = raw_artefact.pop('output_dir')

        try:
            artefact = create_artefact(
                artefact_type_name, name, output_dir, **raw_artefact
            )
        except OutdatedArtefactVersion:
            LOG.warning(
                f"Skipping artefact {name} because it uses an outdated version "
                f"of {artefact_type_name}."
            )
            continue
        artefacts.append(artefact)

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
        file_path, [
            VersionHeader.from_version_number(
                'Artefacts', ARTEFACTS_FILE_VERSION
            ), artefacts
        ]
    )


def initialize_artefacts() -> None:
    """Import plots and tables module to register artefact types."""
    import varats.plot.plots  # pylint: disable=C0415,unused-import
    import varats.table.tables  # pylint: disable=C0415,unused-import
