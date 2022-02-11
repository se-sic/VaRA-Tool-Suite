"""
Driver module for `vara-config`.

This module handles command-line parsing and maps the commands to tool suite
internal functionality.
"""
import copy
import textwrap
import typing as tp

import click
import yaml
from benchbuild.utils.settings import ConfigDumper, Configuration

from varats.utils.settings import vara_cfg, save_config


@click.group("vara-config")
def main() -> None:
    """
    Main function for managing the VaRA-TS config.

    `vara-config`
    """


def __get_config_for_path(option_path: tp.List[str]) -> Configuration:
    config = vara_cfg()
    for opt in option_path:
        config = config[opt]
    return config


def __dump_config_to_string(config: Configuration) -> str:
    """
    Create a yaml dump of a config object.

    See ``benchbuild.utils.settings.Configuration.store()``.
    """

    selfcopy = copy.deepcopy(config)
    selfcopy.filter_exports()

    return str(
        yaml.dump(
            selfcopy.node,
            width=80,
            indent=4,
            default_flow_style=False,
            Dumper=ConfigDumper
        )
    )


@main.command("set")
@click.argument("config_values", nargs=-1, metavar="KEY=VALUE")
def __config_set(config_values: tp.List[str]) -> None:
    """
    KEY=VALUE Key-Value pairs of configuration options and values.

    Specify the config options like paths, e.g., paper_config/folder. Do not put
    spaces before or after the '=' sign; if a value contains spaces, you should
    define it with double quotes: foo="bar baz".
    """
    if config_values:
        rewritten_config_values = {
            e[0].replace('-', '_'): e[1]
            for e in [arg.split("=") for arg in config_values]
        }
    else:
        rewritten_config_values = {}

    for option, value in rewritten_config_values.items():
        option_path = option.split("/")
        config = __get_config_for_path(option_path[:-1])
        config[option_path[-1]] = value

    save_config()


@main.command("show")
@click.argument("config_options", nargs=-1)
def __config_show(config_options: tp.Optional[tp.List[str]]) -> None:
    """
    \b CONFIG_OPTIONS The config options to show.

    You can also show whole sub-configs. Show the complete config if no options
    are given.
    """
    if not config_options:
        print(__dump_config_to_string(vara_cfg()))
    else:
        options = config_options
        for option in options:
            value = __dump_config_to_string(
                __get_config_for_path(option.split("/"))
            )
            print(f"{option}:\n{textwrap.indent(value, '    ')}")


if __name__ == '__main__':
    main()
