"""Driver module for `vara-cs`."""

import logging
import os
import re
import typing as tp
from argparse import ArgumentParser, ArgumentTypeError, _SubParsersAction
from pathlib import Path

from argparse_utils import enum_action
from plumbum import FG, colors, local

from varats.data.provider.release.release_provider import ReleaseType
from varats.data.report import FileStatusExtension, MetaReport
from varats.paper import paper_config_manager as PCM
from varats.paper.case_study import (
    ExtenderStrategy,
    SamplingMethod,
    extend_case_study,
    generate_case_study,
    load_case_study_from_file,
    store_case_study,
)
from varats.paper.paper_config import get_paper_config
from varats.tools.commit_map import create_lazy_commit_map_loader
from varats.utils.cli_util import cli_list_choice, initialize_cli_tool
from varats.utils.project_util import get_local_project_git_path
from varats.utils.settings import vara_cfg

LOG = logging.getLogger(__name__)


def main() -> None:
    """Allow easier management of case studies."""
    initialize_cli_tool()
    parser = ArgumentParser("vara-cs")
    sub_parsers = parser.add_subparsers(help="Subcommand", dest="subcommand")

    __create_status_parser(sub_parsers)  # vara-cs status
    __create_gen_parser(sub_parsers)  # vara-cs gen
    __create_ext_parser(sub_parsers)  # vara-cs ext
    __create_package_parser(sub_parsers)  # vara-cs package
    __create_view_parser(sub_parsers)  # vara-cs view

    args = {k: v for k, v in vars(parser.parse_args()).items() if v is not None}

    if 'subcommand' not in args:
        parser.print_help()
        return

    if args['subcommand'] == 'status':
        __casestudy_status(args, parser)
    elif args['subcommand'] == 'gen' or args['subcommand'] == 'ext':
        __casestudy_create_or_extend(args, parser)
    elif args['subcommand'] == 'package':
        __casestudy_package(args, parser)
    elif args['subcommand'] == 'view':
        __casestudy_view(args)


def __create_status_parser(sub_parsers: _SubParsersAction) -> None:
    status_parser = sub_parsers.add_parser(
        'status', help="Show status of current case study"
    )
    status_parser.add_argument(
        "report_name",
        help=(
            "Provide a report name to "
            "select which files are considered for the status"
        ),
        choices=MetaReport.REPORT_TYPES.keys(),
        type=str,
        default=".*"
    )
    status_parser.add_argument(
        "--filter-regex",
        help="Provide a regex to filter the shown case studies",
        type=str,
        default=".*"
    )
    status_parser.add_argument(
        "--paper_config",
        help="Use this paper config instead of the configured one",
        default=None
    )
    status_parser.add_argument(
        "-s",
        "--short",
        help="Only print a short summary",
        action="store_true",
        default=False
    )
    status_parser.add_argument(
        "--list-revs",
        help="Print a list of revisions for every stage and every case study",
        action="store_true",
        default=False
    )
    status_parser.add_argument(
        "--ws",
        help="Print status with stage separation",
        action="store_true",
        default=False
    )
    status_parser.add_argument(
        "--sorted",
        help="Sort the revisions in the order they are printed by git log.",
        action="store_true",
        default=False
    )
    status_parser.add_argument(
        "--legend",
        help="Print status with legend",
        action="store_true",
        default=False
    )
    status_parser.add_argument(
        "--force-color",
        help="Force colored output also when not connected to a terminal "
        "(e.g. when piping to less -r).",
        action="store_true",
        default=False
    )


def __add_common_args(sub_parser: ArgumentParser) -> None:
    """Group common args to provide all args on different sub parsers."""
    sub_parser.add_argument(
        "--git-path", help="Path to git repository", default=None
    )
    sub_parser.add_argument(
        "-p", "--project", help="Project name", default=None
    )
    sub_parser.add_argument(
        "--end", help="End of the commit range (inclusive)", default="HEAD"
    )
    sub_parser.add_argument(
        "--start", help="Start of the commit range (exclusive)", default=None
    )
    sub_parser.add_argument(
        "--extra-revs",
        nargs="+",
        default=[],
        help="Add a list of additional revisions to the case-study"
    )
    sub_parser.add_argument(
        "--revs-per-year",
        type=int,
        default=0,
        help="Add this many revisions per year to the case-study."
    )
    sub_parser.add_argument(
        "--revs-year-sep",
        action="store_true",
        default=False,
        help="Separate the revisions in different stages per year "
        "(when using \'--revs-per-year\')."
    )
    sub_parser.add_argument(
        "--num-rev",
        type=int,
        default=10,
        help="Number of revisions to select."
    )
    sub_parser.add_argument(
        "--ignore-blocked",
        action="store_true",
        default=False,
        help="Ignore revisions that are marked as blocked."
    )


def __create_gen_parser(sub_parsers: _SubParsersAction) -> None:
    gen_parser = sub_parsers.add_parser('gen', help="Generate a case study.")
    gen_parser.add_argument(
        "paper_config_path",
        help="Path to paper_config folder (e.g., paper_configs/ase-17)"
    )
    gen_parser.add_argument("distribution", action=enum_action(SamplingMethod))
    gen_parser.add_argument(
        "-v", "--version", type=int, default=0, help="Case study version."
    )
    __add_common_args(gen_parser)


def __create_ext_parser(sub_parsers: _SubParsersAction) -> None:
    ext_parser = sub_parsers.add_parser(
        'ext', help="Extend an existing case study."
    )
    ext_parser.add_argument("case_study_path", help="Path to case_study")
    ext_parser.add_argument(
        "strategy",
        action=enum_action(ExtenderStrategy),
        help="Extender strategy"
    )
    ext_parser.add_argument(
        "--distribution", action=enum_action(SamplingMethod)
    )
    ext_parser.add_argument("--release-type", action=enum_action(ReleaseType))
    ext_parser.add_argument(
        "--merge-stage",
        default=-1,
        type=int,
        help="Merge the new revision(s) into stage `n`; defaults to last stage."
    )
    ext_parser.add_argument(
        "--new-stage",
        help="Add the new revision(s) to a new stage.",
        default=False,
        action='store_true'
    )
    ext_parser.add_argument(
        "--boundary-gradient",
        type=int,
        default=5,
        help="Maximal expected gradient in percent between " +
        "two revisions, e.g., 5 for 5%%"
    )
    ext_parser.add_argument(
        "--plot-type", help="Plot to calculate new revisions from."
    )
    ext_parser.add_argument(
        "--report-type",
        help="Passed to the plot given via --plot-type.",
        default="EmptyReport"
    )
    ext_parser.add_argument(
        "--result-folder", help="Folder in which to search for result files."
    )
    __add_common_args(ext_parser)


def __create_package_parser(sub_parsers: _SubParsersAction) -> None:
    package_parser = sub_parsers.add_parser(
        'package', help="Case study packaging util"
    )
    package_parser.add_argument("-o", "--output", help="Output file")
    package_parser.add_argument(
        "--filter-regex",
        help="Provide a regex to only include case "
        "studies that match the filter.",
        type=str,
        default=".*"
    )
    package_parser.add_argument(
        "--report-names",
        help=(
            "Provide a report name to "
            "select which files are considered for the status"
        ),
        choices=MetaReport.REPORT_TYPES.keys(),
        type=str,
        nargs="*",
        default=[]
    )


def __create_view_parser(sub_parsers: _SubParsersAction) -> None:
    view_parser = sub_parsers.add_parser('view', help="View report files.")
    view_parser.add_argument(
        "report_type",
        help="Report type of the result files.",
        choices=MetaReport.REPORT_TYPES.keys(),
        type=str
    )
    view_parser.add_argument(
        "project", help="Project to view result files for."
    )
    view_parser.add_argument(
        "commit_hash", help="Commit hash to view result files for.", nargs='?'
    )
    view_parser.add_argument(
        "--newest-only",
        action="store_true",
        default=False,
        help="Only report the newest file for each matched commit hash"
    )


def __casestudy_status(
    args: tp.Dict[str, tp.Any], parser: ArgumentParser
) -> None:
    if args.get("force_color", False):
        colors.use_color = True
    if 'paper_config' in args:
        vara_cfg()['paper_config']['current_config'] = args['paper_config']
    if args['short'] and args['list_revs']:
        parser.error(
            "At most one argument of: --short, --list-revs can be used."
        )
    if args['short'] and args['ws']:
        parser.error("At most one argument of: --short, --ws can be used.")
    PCM.show_status_of_case_studies(
        args['report_name'], args['filter_regex'], args['short'],
        args['sorted'], args['list_revs'], args['ws'], args['legend']
    )


def __casestudy_create_or_extend(
    args: tp.Dict[str, tp.Any], parser: ArgumentParser
) -> None:
    if "project" not in args and "git_path" not in args:
        parser.error("need --project or --git-path")
        return

    if "project" in args and "git_path" not in args:
        args['git_path'] = str(get_local_project_git_path(args['project']))

    if "git_path" in args and "project" not in args:
        args['project'] = Path(args['git_path']).stem.replace("-HEAD", "")

    args['get_cmap'] = create_lazy_commit_map_loader(
        args['project'], args.get('cmap', None), args['end'],
        args['start'] if 'start' in args else None
    )
    cmap = args['get_cmap']()

    if args['subcommand'] == 'ext':
        case_study = load_case_study_from_file(Path(args['case_study_path']))

        # If no merge_stage was specified add it to the last
        if args['merge_stage'] == -1:
            args['merge_stage'] = max(case_study.num_stages - 1, 0)
        # If + was specified we add a new stage
        if args['new_stage']:
            args['merge_stage'] = case_study.num_stages

        # Setup default result folder
        if 'result_folder' not in args and args[
            'strategy'] is ExtenderStrategy.smooth_plot:
            args['project'] = case_study.project_name
            args['result_folder'] = str(vara_cfg()['result_dir']
                                       ) + "/" + args['project']
            LOG.info(f"Result folder defaults to: {args['result_folder']}")

        extend_case_study(case_study, cmap, args['strategy'], **args)

        store_case_study(case_study, Path(args['case_study_path']))
    else:
        args['paper_config_path'] = Path(args['paper_config_path'])
        if not args['paper_config_path'].exists():
            raise ArgumentTypeError("Paper path does not exist")

        # Specify merge_stage as 0 for creating new case studies
        args['merge_stage'] = 0

        case_study = generate_case_study(
            args['distribution'], cmap, args['version'], args['project'], **args
        )

        store_case_study(case_study, args['paper_config_path'])


def __casestudy_package(
    args: tp.Dict[str, tp.Any], parser: ArgumentParser
) -> None:
    output_path = Path(args["output"])
    if output_path.suffix == '':
        output_path = Path(str(output_path) + ".zip")
    if output_path.suffix == '.zip':
        vara_root = Path(str(vara_cfg()["config_file"])).parent
        if Path(os.getcwd()) != vara_root:
            LOG.info(
                f"Packaging needs to be called from VaRA root dir, "
                f"changing dir to {vara_root}"
            )
            os.chdir(vara_root)

        PCM.package_paper_config(
            output_path, re.compile(args['filter_regex']), args['report_names']
        )
    else:
        parser.error(
            "--output has the wrong file type extension. "
            "Please do not provide any other file type extension than .zip"
        )


def __init_commit_hash(args: tp.Dict[str, tp.Any]) -> str:
    result_file_type = MetaReport.REPORT_TYPES[args["report_type"]]
    project_name = args["project"]
    if "commit_hash" not in args:
        # Ask the user to provide a commit hash
        print("No commit hash was provided.")
        commit_hash = ""
        paper_config = get_paper_config()

        available_commit_hashes = []
        # Compute available commit hashes
        for case_study in paper_config.get_case_studies(project_name):
            available_commit_hashes.extend(
                case_study.get_revisions_status(
                    result_file_type, tag_blocked=False
                )
            )

        max_num_hashes = 42
        if len(available_commit_hashes) > max_num_hashes:
            print("Found to many commit hashes, truncating selection...")

        # Create call backs for cli choice
        def set_commit_hash(
            choice_pair: tp.Tuple[str, FileStatusExtension]
        ) -> None:
            nonlocal commit_hash
            commit_hash = choice_pair[0][:10]

        longest_file_status_extension = max([
            len(status.get_colored_status())
            for status in FileStatusExtension.get_physical_file_statuses()
        ])

        def result_file_to_list_entry(
            commit_status_pair: tp.Tuple[str, FileStatusExtension]
        ) -> str:
            status = commit_status_pair[1].get_colored_status().rjust(
                longest_file_status_extension, " "
            )
            return f"[{status}] {commit_status_pair[0][:10]}"

        # Ask user which commit we should use
        try:
            cli_list_choice(
                "Please select a hash:",
                available_commit_hashes[:max_num_hashes],
                result_file_to_list_entry,
                set_commit_hash,
                start_label=1,
                default=1,
            )
        except EOFError:
            raise LookupError
        if commit_hash == "":
            print("Could not find processed commit hash.")
            raise LookupError
        return commit_hash
    return tp.cast(str, args["commit_hash"])


def __casestudy_view(args: tp.Dict[str, tp.Any]) -> None:
    result_file_type = MetaReport.REPORT_TYPES[args["report_type"]]
    project_name = args["project"]

    try:
        commit_hash = __init_commit_hash(args)
    except LookupError:
        return

    result_files = PCM.get_result_files(
        result_file_type, project_name, commit_hash,
        args.get("newest_only", False)
    )
    result_files.sort(
        key=lambda report_file: report_file.stat().st_mtime_ns, reverse=True
    )

    if not result_files:
        print("No matching result files found.")
        return

    print(
        f"Found {len(result_files)} matching result files (newest to oldest):"
    )

    longest_file_status_extension = max([
        len(status.get_colored_status())
        for status in FileStatusExtension.get_physical_file_statuses()
    ])

    def result_file_to_list_entry(result_file: Path) -> str:
        status = (
            result_file_type.get_status_from_result_file(result_file.name)
        ).get_colored_status().rjust(longest_file_status_extension, " ")
        return f"[{status}] {result_file.name}"

    def open_in_editor(result_file: Path) -> None:
        _ = editor[str(result_file)] & FG

    editor_name = local.env["EDITOR"]
    if not editor_name:
        editor_name = "vim"
    editor = local[editor_name]
    try:
        cli_list_choice(
            "Select a number to open a file",
            result_files,
            result_file_to_list_entry,
            open_in_editor,
            start_label=1,
            default=1,
            repeat=True
        )
    except EOFError:
        return


if __name__ == '__main__':
    main()
