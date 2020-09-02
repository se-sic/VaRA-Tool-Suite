"""
Driver module for `vara-config`.

This module handles command-line parsing and maps the commands to tool suite
internal functionality.
"""
import argparse
import copy
import textwrap
import typing as tp

import yaml
from benchbuild.utils.settings import ConfigDumper, Configuration

from varats.utils.settings import vara_cfg, save_config


def main() -> None:
    """
    Main function for managing the VaRA-TS config.

    `vara-config`
    """
    parser = argparse.ArgumentParser("vara-config")

    sub_parsers = parser.add_subparsers(help="Subcommand", dest="subcommand")

    # vara-conf set
    set_parser = sub_parsers.add_parser(
        'set', help="Set one or more config options."
    )
    set_parser.add_argument(
        "config_values",
        metavar="KEY=VALUE",
        nargs=argparse.REMAINDER,
        help=(
            "Key-Value pairs of configuration options and values."
            "Specify the config options like paths, e.g., paper_config/folder."
            "Do not put spaces before or after the '=' sign; if a value "
            "contains spaces, you should define it with double quotes: "
            'foo="bar baz".'
        )
    )

    # vara-art show
    show_parser = sub_parsers.add_parser(
        'show', help="Show values of config options."
    )
    show_parser.add_argument(
        "config_options",
        nargs="*",
        help="The config options to show. You can also show whole sub-configs."
        "Show the complete config if no options are given.",
        type=str
    )

    args = {k: v for k, v in vars(parser.parse_args()).items() if v is not None}

    if 'subcommand' not in args:
        parser.print_help()
        return

    if args['subcommand'] == 'set':
        __config_set(args)
    elif args['subcommand'] == 'show':
        __config_show(args)


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


def __config_set(args: tp.Dict[str, tp.Any]) -> None:
    if "config_values" in args.keys():
        config_values = {
            e[0].replace('-', '_'): e[1]
            for e in [arg.split("=") for arg in args["config_values"]]
        }
    else:
        config_values = {}

    for option, value in config_values.items():
        option_path = option.split("/")
        config = __get_config_for_path(option_path[:-1])
        config[option_path[-1]] = value

    save_config()


def __config_show(args: tp.Dict[str, tp.Any]) -> None:
    if not "config_options" in args or len(args["config_options"]) == 0:
        print(__dump_config_to_string(vara_cfg()))
    else:
        options = args["config_options"]
        for option in options:
            value = __dump_config_to_string(
                __get_config_for_path(option.split("/"))
            )
            print(f"{option}:\n{textwrap.indent(value, '    ')}")


if __name__ == '__main__':
    main()
