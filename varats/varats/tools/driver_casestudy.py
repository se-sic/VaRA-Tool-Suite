"""Driver module for `vara-cs`."""

import logging
import os
import re
import typing as tp
from argparse import ArgumentParser, ArgumentTypeError, _SubParsersAction
from enum import Enum
from pathlib import Path

import click
from argparse_utils import enum_action
from plumbum import FG, colors, local

from varats.base.sampling_method import NormalSamplingMethod
from varats.data.discover_reports import initialize_reports
from varats.mapping.commit_map import create_lazy_commit_map_loader
from varats.paper.case_study import load_case_study_from_file, store_case_study
from varats.paper_mgmt import paper_config_manager as PCM
from varats.paper_mgmt.case_study import (
    get_revisions_status_for_case_study,
    ExtenderStrategy,
    extend_case_study,
    generate_case_study,
)
from varats.paper_mgmt.paper_config import get_paper_config
from varats.plots.discover_plots import initialize_plots
from varats.project.project_util import get_local_project_git_path
from varats.projects.discover_projects import initialize_projects
from varats.provider.release.release_provider import ReleaseType
from varats.report.report import FileStatusExtension, BaseReport, ReportFilename
from varats.tools.tool_util import configuration_lookup_error_handler
from varats.ts_utils.cli_util import (
    cli_list_choice,
    initialize_cli_tool,
    cli_yn_choice,
)
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import vara_cfg

LOG = logging.getLogger(__name__)


@click.group()
def main() -> None:
    """Allow easier management of case studies."""
    initialize_cli_tool()
    initialize_projects()
    initialize_reports()
    initialize_plots()  # needed for vara-cs ext smooth_plot


def mai_nold() -> None:
    """Allow easier management of case studies."""
    initialize_cli_tool()
    initialize_projects()
    initialize_reports()
    initialize_plots()  # needed for vara-cs ext smooth_plot
    parser = ArgumentParser("vara-cs")
    sub_parsers = parser.add_subparsers(help="Subcommand", dest="subcommand")

    __create_gen_parser(sub_parsers)  # vara-cs gen
    __create_ext_parser(sub_parsers)  # vara-cs ext
    __create_package_parser(sub_parsers)  # vara-cs package
    __create_view_parser(sub_parsers)  # vara-cs view
    __create_cleanup_parser(sub_parsers)  # vara-cs cleanup

    args = {k: v for k, v in vars(parser.parse_args()).items() if v is not None}
    if 'subcommand' not in args:
        parser.print_help()
        return
    __casestudy_exec_command(args, parser)


@configuration_lookup_error_handler
def __casestudy_exec_command(
    args: tp.Dict[str, tp.Any], parser: ArgumentParser
) -> None:
    if args['subcommand'] == 'status':
        __casestudy_status(args, parser)
    elif args['subcommand'] == 'gen' or args['subcommand'] == 'ext':
        __casestudy_create_or_extend(args, parser)
    elif args['subcommand'] == 'package':
        __casestudy_package(args, parser)
    elif args['subcommand'] == 'view':
        __casestudy_view(args)
    elif args['subcommand'] == 'cleanup':
        __casestudy_cleanup(args, parser)


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
    gen_parser.add_argument(
        "distribution",
        choices=[
            x.name()
            for x in NormalSamplingMethod.normal_sampling_method_types()
        ]
    )
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
        action=enum_action(ExtenderStrategy, str.upper),
        help="Extender strategy"
    )
    ext_parser.add_argument(
        "--distribution",
        choices=[
            x.name()
            for x in NormalSamplingMethod.normal_sampling_method_types()
        ]
    )
    ext_parser.add_argument(
        "--release-type", action=enum_action(ReleaseType, str.upper)
    )
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
        choices=BaseReport.REPORT_TYPES.keys(),
        type=str,
        nargs="*",
        default=[]
    )


def __create_view_parser(sub_parsers: _SubParsersAction) -> None:
    view_parser = sub_parsers.add_parser('view', help="View report files.")
    view_parser.add_argument(
        "report_type",
        help="Report type of the result files.",
        choices=BaseReport.REPORT_TYPES.keys(),
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


def __create_cleanup_parser(sub_parsers: _SubParsersAction) -> None:
    cleanup_parser = sub_parsers.add_parser(
        'cleanup', help="Cleanup report files."
    )
    cleanup_parser.add_argument(
        "cleanup_type",
        help="The type of the performed cleanup action.",
        action=enum_action(CleanupType, str.upper)
    )
    cleanup_parser.add_argument(
        "-f",
        "--filter-regex",
        help="Regex to determine which report files should be deleted.",
        default="",
        type=str
    )
    cleanup_parser.add_argument(
        "--silent",
        action="store_true",
        default=False,
        help="Hide the output of the matching filenames."
    )


@main.command("status")
@click.argument(
    "report_type", type=click.Choice(list(BaseReport.REPORT_TYPES.keys()))
)
@click.option(
    "--filter-regex",
    help="Provide a regex to filter the shown case studies",
    default=".*"
)
@click.option(
    "--paper-config",
    help="Use this paper config instead of the configured one",
    default=None
)
@click.option("-s", "--short", is_flag=True, help="Only print a short summary")
@click.option(
    "--list-revs",
    is_flag=True,
    help="Print a list of revisions for every stage and every case study"
)
@click.option("--ws", is_flag=True, help="Print status with stage separation")
@click.option(
    "--sorted",
    "sort_revs",
    is_flag=True,
    help="Sort the revisions in the order they are printed by git log."
)
@click.option("--legend", is_flag=True, help="Print status with legend")
@click.option(
    "--force-color",
    is_flag=True,
    help="Force colored output also when not connected to a terminal "
    "(e.g. when piping to less -r)."
)
def __casestudy_status(
    report_type: str, filter_regex: str, paper_config: str, short: bool,
    list_revs: bool, ws: bool, sort_revs: bool, legend: bool, force_color: bool
) -> None:
    """Show status of case-studies for a specified REPORT TYPE."""
    if force_color:
        colors.use_color = True
    if paper_config:
        vara_cfg()['paper_config']['current_config'] = paper_config
    if short and list_revs:
        click.UsageError(
            "At most one argument of: --short, --list-revs can be used."
        )
    if short and ws:
        click.UsageError("At most one argument of: --short, --ws can be used.")
    PCM.show_status_of_case_studies(
        report_type, filter_regex, short, sort_revs, list_revs, ws, legend
    )


def __casestudy_create_or_extend(
    args: tp.Dict[str, tp.Any], parser: ArgumentParser
) -> None:
    if "project" not in args and "git_path" not in args:
        parser.error("need --project or --git-path")

    if "project" in args and "git_path" not in args:
        args['git_path'] = str(get_local_project_git_path(args['project']))

    if "git_path" in args and "project" not in args:
        args['project'] = Path(args['git_path']).stem.replace("-HEAD", "")

    args['get_cmap'] = create_lazy_commit_map_loader(
        args['project'], args.get('cmap', None), args['end'],
        args['start'] if 'start' in args else None
    )
    cmap = args['get_cmap']()

    # Rewrite requested distribution with initialized object
    if 'distribution' in args:
        sampling_method = NormalSamplingMethod.get_sampling_method_type(
            args['distribution']
        )()
        args['distribution'] = sampling_method

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
            'strategy'] is ExtenderStrategy.SMOOTH_PLOT:
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
            sampling_method, cmap, args['version'], args['project'], **args
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


def __init_commit_hash(
    report_type: tp.Type[BaseReport], project: str, commit_hash: str
) -> ShortCommitHash:
    if not commit_hash:
        # Ask the user to provide a commit hash
        print("No commit hash was provided.")
        commit_hash: tp.Optional[ShortCommitHash] = None
        paper_config = get_paper_config()
        available_commit_hashes = []
        # Compute available commit hashes
        for case_study in paper_config.get_case_studies(project):
            available_commit_hashes.extend(
                get_revisions_status_for_case_study(
                    case_study, report_type, tag_blocked=False
                )
            )

        max_num_hashes = 42
        if len(available_commit_hashes) > max_num_hashes:
            print("Found to many commit hashes, truncating selection...")

        # Create call backs for cli choice
        def set_commit_hash(
            choice_pair: tp.Tuple[ShortCommitHash, FileStatusExtension]
        ) -> None:
            nonlocal commit_hash
            commit_hash = choice_pair[0]

        statuses = FileStatusExtension.get_physical_file_statuses().union(
            FileStatusExtension.get_virtual_file_statuses()
        )

        longest_file_status_extension = max([
            len(status.name) for status in statuses
        ])

        def result_file_to_list_entry(
            commit_status_pair: tp.Tuple[ShortCommitHash, FileStatusExtension]
        ) -> str:
            status = commit_status_pair[1].get_colored_status().rjust(
                longest_file_status_extension +
                commit_status_pair[1].num_color_characters(), " "
            )

            return f"[{status}] {commit_status_pair[0]}"

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
        except EOFError as exc:
            raise LookupError from exc
        if not commit_hash:
            print("Could not find processed commit hash.")
            raise LookupError
        return commit_hash
    return ShortCommitHash(commit_hash)


@main.command("view")
@click.argument(
    "report-type", type=click.Choice(list(BaseReport.REPORT_TYPES.keys()))
)
@click.argument("project")
@click.argument("commit-hash", required=False)
@click.option("--newest-only", is_flag=True)
def __casestudy_view(
    report_type: str, project: str, commit_hash: str, newest_only: bool
) -> None:
    result_file_type = BaseReport.REPORT_TYPES[report_type]
    try:
        commit_hash = __init_commit_hash(result_file_type, project, commit_hash)
    except LookupError:
        return

    result_files = PCM.get_result_files(
        result_file_type, project, commit_hash, newest_only
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

    statuses = FileStatusExtension.get_physical_file_statuses().union(
        FileStatusExtension.get_virtual_file_statuses()
    )

    longest_file_status_extension = max([
        len(status.name) for status in statuses
    ])

    def result_file_to_list_entry(result_file: Path) -> str:
        file_status = ReportFilename(result_file.name).file_status
        status = (
            file_status.get_colored_status().rjust(
                longest_file_status_extension +
                file_status.num_color_characters(), " "
            )
        )
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


@main.group()
def cleanup() -> None:
    return


@cleanup.command("old")
def _remove_old_result_files() -> None:
    paper_config = get_paper_config()
    result_dir = Path(str(vara_cfg()['result_dir']))
    for case_study in paper_config.get_all_case_studies():
        old_files: tp.List[Path] = []
        newer_files: tp.Dict[ShortCommitHash, Path] = {}
        result_dir_cs = result_dir / case_study.project_name
        if not result_dir_cs.exists():
            continue
        for opt_res_file in result_dir_cs.iterdir():
            report_file = ReportFilename(opt_res_file.name)
            commit_hash = report_file.commit_hash
            if case_study.has_revision(commit_hash):
                current_file = newer_files.get(commit_hash)
                if current_file is None:
                    newer_files[commit_hash] = opt_res_file
                else:
                    if (
                        current_file.stat().st_mtime_ns <
                        opt_res_file.stat().st_mtime_ns
                    ):
                        newer_files[commit_hash] = opt_res_file
                        old_files.append(current_file)
                    else:
                        old_files.append(opt_res_file)
        for file in old_files:
            if file.exists():
                os.remove(file)


def _find_result_dir_paths_of_projects() -> tp.List[Path]:
    result_dir_path = Path(vara_cfg()["result_dir"].value)
    existing_paper_config_result_dir_paths = []
    paper_config = get_paper_config()
    project_names = [
        cs.project_name for cs in paper_config.get_all_case_studies()
    ]
    for project_name in project_names:
        path = Path(result_dir_path / project_name)
        if Path.exists(path):
            existing_paper_config_result_dir_paths.append(path)

    return existing_paper_config_result_dir_paths


@cleanup.command("error")
def _remove_error_result_files() -> None:
    result_dir_paths = _find_result_dir_paths_of_projects()

    for result_dir_path in result_dir_paths:
        result_file_names = os.listdir(result_dir_path)

        for result_file_name in result_file_names:
            report_file_name = ReportFilename(result_file_name)
            if report_file_name.is_result_file() and (
                report_file_name.has_status_compileerror() or
                report_file_name.has_status_failed()
            ):
                os.remove(result_dir_path / result_file_name)


@cleanup.command("regex")
@click.option(
    "--filter-regex",
    "-f",
    "regex_filter",
    prompt="Specify a regex for the filenames to delete"
)
@click.option(
    "--silent", help="Hide the output of the matching filenames", is_flag=True
)
def _remove_result_files_by_regex(regex_filter: str, hide: bool) -> None:
    result_dir_paths = _find_result_dir_paths_of_projects()

    for result_dir_path in result_dir_paths:
        result_file_names = os.listdir(result_dir_path)
        files_to_delete: tp.List[str] = []
        for result_file_name in result_file_names:
            match = re.match(regex_filter, result_file_name)
            if match is not None:
                files_to_delete.append(result_file_name)
        if not files_to_delete:
            print(f"No matching result files in {result_dir_path} found.")
            continue
        if not hide:
            for file_name in files_to_delete:
                print(f"{file_name}")
        print(
            f"Found {len(files_to_delete)} matching"
            "result files in {result_dir_path}:"
        )

        try:
            if cli_yn_choice("Do you want to delete these files", "n"):
                for file_name in files_to_delete:
                    if Path.exists(result_dir_path / file_name):
                        os.remove(result_dir_path / file_name)
        except EOFError:
            continue


class CleanupType(Enum):
    OLD = 0
    ERROR = 1
    REGEX = 2


if __name__ == '__main__':
    main()
