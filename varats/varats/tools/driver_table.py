"""Driver module for `vara-table`."""

import argparse
import logging
import typing as tp

from argparse_utils import enum_action

from varats.data.discover_reports import initialize_reports
from varats.projects.discover_projects import initialize_projects
from varats.table.tables import TableRegistry, build_tables, TableFormat
from varats.tables.discover_tables import initialize_tables
from varats.ts_utils.cli_util import initialize_cli_tool

LOG = logging.getLogger(__name__)


def main() -> None:
    """
    Main function for the table generator.

    `vara-table`
    """
    initialize_cli_tool()
    initialize_projects()
    initialize_reports()
    initialize_tables()
    parser = argparse.ArgumentParser("vara-table")
    parser.add_argument(
        "table_type",
        help="Table to generate." + TableRegistry.get_table_types_help_string()
    )
    parser.add_argument(
        "-r", "--result-output", help="Folder with result files"
    )
    parser.add_argument("-p", "--project", help="Project name")
    parser.add_argument(
        "-v",
        "--view",
        help="Print the table to the console instead of saving it",
        action='store_true',
        default=False
    )
    parser.add_argument("--cs-path", help="Path to case_study", default=None)
    parser.add_argument(
        "--paper-config",
        help="Generate tables for all case studies in the current paper config",
        action='store_true',
        default=False
    )
    parser.add_argument(
        "--wrap-document",
        help="Wrap the table in a full compilable document (for latex tables)",
        action='store_true',
        default=False
    )
    parser.add_argument(
        "--report-type",
        help="The report type to generate the table for."
        "Tables may ignore this option.",
        default="EmptyReport"
    )
    parser.add_argument(
        "--output-format",
        help="The format the table should have",
        action=enum_action(TableFormat)
    )
    parser.add_argument(
        "extra_args",
        metavar="KEY=VALUE",
        nargs=argparse.REMAINDER,
        help=(
            "Provide additional arguments that will be passed to the table "
            "class. (do not put spaces before or after the '=' sign). "
            "If a value contains spaces, you should define it "
            'with double quotes: foo="bar baz".'
        )
    )

    args = {k: v for k, v in vars(parser.parse_args()).items() if v is not None}

    __table(args)


def __table(args: tp.Dict[str, tp.Any]) -> None:
    if 'extra_args' in args.keys():
        extra_args = {
            e[0].replace('-', '_'): e[1]
            for e in [arg.split("=") for arg in args['extra_args']]
        }
    else:
        extra_args = {}

    build_tables(**args, **extra_args)


if __name__ == '__main__':
    main()
