"""
Driver module for `vara-art`.

This module handles command-line parsing and maps the commands to tool suite
internal functionality.
"""
import argparse
import logging
import textwrap
import typing as tp

import yaml
from argparse_utils import enum_action

from varats.paper.artefacts import (
    Artefact,
    ArtefactType,
    create_artefact,
    store_artefacts,
)
from varats.paper.paper_config import get_paper_config
from varats.utils.cli_util import initialize_cli_tool

LOG = logging.getLogger(__name__)


def main() -> None:
    """
    Main function for working with artefacts.

    `vara-art`
    """
    initialize_cli_tool()
    parser = argparse.ArgumentParser("vara-art")

    sub_parsers = parser.add_subparsers(help="Subcommand", dest="subcommand")

    # vara-art list
    sub_parsers.add_parser(
        'list', help="List all artefacts of the current paper config."
    )

    # vara-art show
    show_parser = sub_parsers.add_parser(
        'show', help="Show detailed insformation about artefacts."
    )
    show_parser.add_argument(
        "names", nargs='+', help="The names of the artefacts to show."
    )

    # vara-art generate
    generate_parser = sub_parsers.add_parser(
        'generate',
        help="Generate artefacts. By default, all artefacts are generated."
    )
    generate_parser.add_argument(
        "--only",
        nargs='+',
        help="Only generate artefacts with the given names."
    )

    # vara-art add
    add_parser = sub_parsers.add_parser(
        'add',
        help=(
            "Add a new artefact to the current paper config or edit an "
            "existing artefacts."
        )
    )
    add_parser.add_argument(
        "artefact_type",
        help="The type of the new artefact.",
        action=enum_action(ArtefactType)
    )
    add_parser.add_argument(
        "name",
        help="The name for the new artefact. "
        "If an artefact with this name already exists, it is overridden.",
        type=str
    )
    add_parser.add_argument(
        "--output-path",
        help=(
            "The output file for the new artefact. This is relative to "
            "`artefacts_dir/current_config` from the current `.varats.yml`."
        ),
        type=str,
        default="."
    )
    add_parser.add_argument(
        "extra_args",
        metavar="KEY=VALUE",
        nargs=argparse.REMAINDER,
        help=(
            "Provide additional arguments that will be passed to the class "
            "that generates the artefact. (do not put spaces before or after "
            "the '=' sign). If a value contains spaces, you should define it "
            'with double quotes: foo="bar baz".'
        )
    )

    args = {k: v for k, v in vars(parser.parse_args()).items() if v is not None}

    if 'subcommand' not in args:
        parser.print_help()
        return

    if args['subcommand'] == 'list':
        __artefact_list()
    elif args['subcommand'] == 'show':
        __artefact_show(args)
    elif args['subcommand'] == 'generate':
        __artefact_generate(args)
    elif args['subcommand'] == 'add':
        __artefact_add(args)


def __artefact_list() -> None:
    paper_config = get_paper_config()

    for artefact in paper_config.artefacts:
        print(f"{artefact.name} [{artefact.artefact_type.name}]")


def __artefact_show(args: tp.Dict[str, tp.Any]) -> None:
    paper_config = get_paper_config()
    for name in args['names']:
        artefact = paper_config.artefacts.get_artefact(name)
        if artefact:
            print(f"Artefact '{name}':")
            print(textwrap.indent(yaml.dump(artefact.get_dict()), '  '))
        else:
            print(f"There is no artefact with the name {name}.")


def __artefact_generate(args: tp.Dict[str, tp.Any]) -> None:
    artefacts: tp.Iterable[Artefact]

    if 'only' in args.keys():
        artefacts = [
            art for art in get_paper_config().get_all_artefacts()
            if art.name in args['only']
        ]
    else:
        artefacts = get_paper_config().get_all_artefacts()
    for artefact in artefacts:
        LOG.info(
            f"Generating artefact {artefact.name} in location "
            f"{artefact.output_path}"
        )
        artefact.generate_artefact()


def __artefact_add(args: tp.Dict[str, tp.Any]) -> None:
    paper_config = get_paper_config()

    if 'extra_args' in args.keys():
        extra_args = {
            e[0].replace('-', '_'): e[1]
            for e in [arg.split("=") for arg in args['extra_args']]
        }
    else:
        extra_args = {}

    name = args['name']
    if paper_config.artefacts.get_artefact(name):
        LOG.info(f"Updating existing artefact '{name}'.")
    else:
        LOG.info(f"Creating new artefact '{name}'.")
    artefact = create_artefact(
        args['artefact_type'], name, args['output_path'], **extra_args
    )
    paper_config.add_artefact(artefact)
    store_artefacts(paper_config.artefacts, paper_config.path)


if __name__ == '__main__':
    main()
