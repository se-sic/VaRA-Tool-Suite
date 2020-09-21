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

    # TODO: impl class


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
        yaml.dump(get_configuration_map_as_yaml_doc(configuration_map), stream)


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


def get_configuration_map_as_yaml_doc(
    configuration_map: ConfigurationMap
) -> tp.Dict[str, tp.Any]:
    """
    Dumps the `ConfigurationMap` as a yaml document.

    Args:
        configuration_map: to dump

    Returns: yaml representation of the configuration map
    """

    # TODO impl
