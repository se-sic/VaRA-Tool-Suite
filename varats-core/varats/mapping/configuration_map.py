"""Configuration map module."""
import abc
import logging
import typing as tp
from pathlib import Path

import yaml

from varats.base.configuration import Configuration
from varats.base.version_header import VersionHeader

LOG = logging.getLogger(__name__)


class ConfigurationMap():
    """A configuration map builds a relation between an unique ID and the
    corresponding project configuration."""

    def __init__(self) -> None:
        self.__confgurations: tp.Dict[int, Configuration] = dict()

    def add_configuration(self, config: Configuration) -> int:
        """
        Add a new configuration to the map.

        Args:
            config: the configuration to add

        Returns: unique ID for the added configuration
        """
        next_id = self.__get_next_id()
        self.__confgurations[next_id] = config
        return next_id

    def get_configuration(self, config_id: int) -> tp.Optional[Configuration]:
        """
        Look up the `Configuration` with the corresponding config_id.

        Args:
            config_id: unique identifier for the Configuration

        Returns: the configuration if found, otherwise, None
        """
        if config_id in self.__confgurations.keys():
            return self.__confgurations[config_id]

        return None

    def configurations(self) -> tp.ValuesView[Configuration]:
        """All configurations stored in the config map."""
        return self.__confgurations.values()

    def id_config_tuples(self) -> tp.ItemsView[int, Configuration]:
        """All id configuration pairs stored in the config map."""
        return self.__confgurations.items()

    def __get_next_id(self) -> int:
        return len(self.__confgurations.keys())


def load_configuration_map(file_path: Path) -> ConfigurationMap:
    """
    Load a configuration map from a file.

    Args:
        file_path: to the configuration map file

    Returns: a new `ConfigurationMap` based on the parsed file
    """
    with open(file_path, 'r') as stream:
        documents = yaml.load_all(stream, Loader=yaml.CLoader)
        version_header = VersionHeader(next(documents))
        version_header.raise_if_not_type("ConfigurationMap")
        version_header.raise_if_version_is_less_than(1)

        return create_configuration_map_from_yaml_doc(next(documents))


def store_configuration_map(
    configuration_map: ConfigurationMap, file_path: Path
) -> None:
    """
    Store a `ConfigurationMap` to a file.

    Args:
        configuration_map: to store
        file_path: to the file
    """
    if file_path.suffix not in ["yml", "yaml"]:
        LOG.warning(
            "ConfigurationMap file path does not end in "
            ".yaml or .yml but dumped file is of type yaml."
        )

    with open(file_path, 'w') as stream:
        version_header = VersionHeader.from_version_number(
            "ConfigurationMap", 1
        )
        yaml.dump(version_header.get_dict(), stream)
        yaml.dump({
            id_config_pair[0]: id_config_pair[1]
            for id_config_pair in configuration_map.id_config_tuples()
        }, stream)


def create_configuration_map_from_yaml_doc(
    yaml_doc: tp.Dict[str, tp.Any]
) -> ConfigurationMap:
    """
    Create a configuration map from a yaml document.

    Args:
        yaml_doc: containing the configuration map

    Returns: a new `ConfigurationMap` based on the parsed doc
    """

    # TODO impl
