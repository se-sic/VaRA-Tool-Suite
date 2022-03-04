"""Configuration map module."""
import logging
import typing as tp
from pathlib import Path

import yaml

from varats.base.configuration import Configuration, DummyConfiguration
from varats.base.version_header import VersionHeader
from varats.utils.exceptions import ConfigurationMapConfigIDMissmatch

LOG = logging.getLogger(__name__)


class ConfigurationMap():
    """A configuration map builds a relation between a unique ID and the
    corresponding project configuration."""

    DUMMY_CONFIG_ID = -1

    def __init__(self) -> None:
        self.__configurations: tp.Dict[int, Configuration] = {}

    def add_configuration(self, config: Configuration) -> int:
        """
        Add a new configuration to the map.

        Args:
            config: the configuration to add

        Returns: unique ID for the added configuration
        """
        next_id = self.__get_next_id()
        self.__configurations[next_id] = config
        return next_id

    def get_configuration(self, config_id: int) -> tp.Optional[Configuration]:
        """
        Look up the `Configuration` with the corresponding config_id.

        Args:
            config_id: unique identifier for the Configuration

        Returns: the configuration if found, otherwise, None
        """
        if config_id == self.DUMMY_CONFIG_ID:
            return DummyConfiguration()

        if config_id in self.__configurations.keys():
            return self.__configurations[config_id]

        return None

    def configurations(self) -> tp.ValuesView[Configuration]:
        """All configurations stored in the config map."""
        return self.__configurations.values()

    def id_config_tuples(self) -> tp.ItemsView[int, Configuration]:
        """All id configuration pairs stored in the config map."""
        return self.__configurations.items()

    def ids(self) -> tp.List[int]:
        return list(self.__configurations.keys())

    def __str__(self) -> str:
        return str(self.__configurations)

    def __get_next_id(self) -> int:
        return len(self.__configurations.keys())


def load_configuration_map(
    file_path: Path, concrete_config_type: tp.Type[Configuration]
) -> ConfigurationMap:
    """
    Load a configuration map from a file.

    Args:
        file_path: to the configuration map file
        concrete_config_type: type of the configuration objects that should be
                              created

    Returns: a new `ConfigurationMap` based on the parsed file
    """
    with open(file_path, 'r') as stream:
        documents = yaml.load_all(stream, Loader=yaml.CLoader)
        version_header = VersionHeader(next(documents))
        version_header.raise_if_not_type("ConfigurationMap")
        version_header.raise_if_version_is_less_than(1)

        return create_configuration_map_from_yaml_doc(
            next(documents), concrete_config_type
        )


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
        yaml.dump_all([
            version_header.get_dict(),
            {
                id_config_pair[0]: id_config_pair[1].dump_to_string()
                for id_config_pair in configuration_map.id_config_tuples()
            }
        ],
                      stream,
                      default_flow_style=False,
                      explicit_start=True,
                      explicit_end=True)


def create_configuration_map_from_yaml_doc(
    yaml_doc: tp.Dict[str, tp.Any], concrete_config_type: tp.Type[Configuration]
) -> ConfigurationMap:
    """
    Create a configuration map from a yaml document.

    Args:
        yaml_doc: containing the configuration map
        concrete_config_type: type of the configuration objects that should be
                              created

    Returns: a new `ConfigurationMap` based on the parsed doc
    """

    new_config_map = ConfigurationMap()

    for config_id in sorted(yaml_doc):
        parsed_config = concrete_config_type.create_configuration_from_str(
            yaml_doc[config_id]
        )

        actual_id = new_config_map.add_configuration(parsed_config)
        if actual_id != int(config_id):
            raise ConfigurationMapConfigIDMissmatch

    return new_config_map
