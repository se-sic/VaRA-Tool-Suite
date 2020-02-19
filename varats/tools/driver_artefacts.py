import argparse

from argparse_utils import enum_action

from varats.paper.artefacts import (ArtefactType, create_artefact,
                                    store_artefacts)
from varats.paper.paper_config import get_paper_config


def main() -> None:
    """
    Main function for working with artefacts.

    `vara-art`
    """
    parser = argparse.ArgumentParser("VaRA artefact manager")
    sub_parsers = parser.add_subparsers(help="Subcommand", dest="subcommand")

    sub_parsers.add_parser(
        'generate',
        help="Generate artefacts. By default, all artefacts are"
        "generated")
    add_parser = sub_parsers.add_parser(
        'add', help="Add a new artefact to the current paper config")
    add_parser.add_argument("artefact_type",
                            help="The type of the new artefact",
                            choices=ArtefactType,
                            action=enum_action(ArtefactType))
    add_parser.add_argument("name",
                            help="The name for the new artefact",
                            type=str)
    add_parser.add_argument(
        "--output_path",
        help=("The output file for the new artefact. "
              "This is relative to `artefacts_dir` in the current `.vara.yml`"),
        type=str,
        default=".")
    add_parser.add_argument("extra_args",
                            metavar="KEY=VALUE",
                            nargs=argparse.REMAINDER,
                            help="Provide additional arguments "
                            "that will be passed to the class that generates"
                            "the artefact. (do not put spaces "
                            "before or after the = sign). "
                            "If a value contains spaces, you should define "
                            'it with double quotes: foo="bar baz".')

    args = {k: v for k, v in vars(parser.parse_args()).items() if v is not None}

    if 'subcommand' not in args:
        parser.print_help()
        return

    extra_args = {
        e[0].replace('-', '_'): e[1]
        for e in [arg.split("=") for arg in args['extra_args']]
    }

    if args['subcommand'] == 'generate':
        for artefact in get_paper_config().get_all_artefacts():
            artefact.generate_artefact()
    elif args['subcommand'] == 'add':
        paper_config = get_paper_config()

        artefact = create_artefact(args['artefact_type'], args['name'],
                                   args['output_path'], **extra_args)
        paper_config.add_artefact(artefact)
        store_artefacts(paper_config.artefacts, paper_config.path)


if __name__ == '__main__':
    main()
