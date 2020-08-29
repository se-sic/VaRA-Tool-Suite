"""Driver module for `vara-table`."""

import argparse
import logging
import typing as tp
from pathlib import Path

from varats.paper.case_study import load_case_study_from_file
from varats.paper.paper_config import get_paper_config
from varats.tables.tables import TableRegistry, build_table
from varats.tools.commit_map import create_lazy_commit_map_loader
from varats.utils.cli_util import initialize_cli_tool
from varats.utils.settings import vara_cfg

LOG = logging.getLogger(__name__)


def main() -> None:
    """
    Main function for the table generator.

    `vara-table`
    """
    initialize_cli_tool()
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
        "--report-type",
        help="The report type to generate the table for."
        "Tables may ignore this option.",
        default="EmptyReport"
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

    # Setup default result folder
    if 'result_output' not in args:
        args['table_dir'] = str(vara_cfg()['tables']['table_dir'])
    else:
        args['table_dir'] = args.pop('result_output')

    if not args["view"]:
        if not Path(args['table_dir']).exists():
            LOG.error(f"Could not find output dir {args['table_dir']}")
            return

        LOG.info(f"Writing tables to: {args['table_dir']}")

    if args['paper_config']:
        paper_config = get_paper_config()
        for case_study in paper_config.get_all_case_studies():
            project_name = case_study.project_name
            args['project'] = project_name
            args['get_cmap'] = create_lazy_commit_map_loader(project_name)
            args['table_case_study'] = case_study
            build_table(**args, **extra_args)
    else:
        if 'project' in args:
            args['get_cmap'] = create_lazy_commit_map_loader(args['project'])
        if 'cs_path' in args:
            case_study_path = Path(args['cs_path'])
            args['table_case_study'] = load_case_study_from_file(
                case_study_path
            )
        else:
            args['table_case_study'] = None
        build_table(**args, **extra_args)


if __name__ == '__main__':
    main()
