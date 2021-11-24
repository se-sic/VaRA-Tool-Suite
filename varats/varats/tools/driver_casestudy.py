"""Driver module for `vara-cs`."""

import logging
import os
import re
import typing as tp
from enum import Enum
from pathlib import Path

import click
from plumbum import FG, colors, local

from varats.base.sampling_method import NormalSamplingMethod
from varats.data.discover_reports import initialize_reports
from varats.mapping.commit_map import create_lazy_commit_map_loader
from varats.paper.case_study import store_case_study
from varats.paper_mgmt import paper_config_manager as PCM
from varats.paper_mgmt.case_study import (
    get_revisions_status_for_case_study,
    generate_case_study,
)
from varats.paper_mgmt.paper_config import get_paper_config
from varats.project.project_util import get_local_project_git_path
from varats.projects.discover_projects import initialize_projects
from varats.report.report import FileStatusExtension, BaseReport, ReportFilename
from varats.tools.tool_util import configuration_lookup_error_handler
from varats.ts_utils.cli_util import (
    cli_list_choice,
    initialize_cli_tool,
    cli_yn_choice,
)
from varats.ts_utils.click_param_types import create_report_type_choice
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import vara_cfg

LOG = logging.getLogger(__name__)


@click.group()
@configuration_lookup_error_handler
def main() -> None:
    """Allow easier management of case studies."""
    initialize_cli_tool()
    initialize_projects()
    initialize_reports()


@main.command("status")
@click.argument("report_type", type=create_report_type_choice())
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
@click.option(
    "--ws",
    "with_stage",
    is_flag=True,
    help="Print status with stage separation"
)
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
    report_type: tp.Type['BaseReport'], filter_regex: str, paper_config: str,
    short: bool, list_revs: bool, with_stage: bool, sort_revs: bool,
    legend: bool, force_color: bool
) -> None:
    """
    Show status of current case study.

    REPORT-NAME: Provide a report name to select which files are considered
    for the status
    """
    if force_color:
        colors.use_color = True
    if paper_config:
        vara_cfg()['paper_config']['current_config'] = paper_config
    if short and list_revs:
        click.UsageError(
            "At most one argument of: --short, --list-revs can be used."
        )
    if short and with_stage:
        click.UsageError("At most one argument of: --short, --ws can be used.")
    PCM.show_status_of_case_studies(
        report_type, filter_regex, short, sort_revs, list_revs, with_stage,
        legend
    )


@main.command("gen")
@click.argument("paper_config_path", type=click.Path(exists=True))
@click.option(
    "--distribution",
    type=click.Choice([
        x.name() for x in NormalSamplingMethod.normal_sampling_method_types()
    ]),
    default=None
)
@click.option(
    "-v", "--version", type=int, default=0, help="Case study version."
)
@click.option("--git-path", help="Path to git repository", default=None)
@click.option("-p", "--project", help="Project name", default=None)
@click.option(
    "--end", help="End of the commit range (inclusive)", default="HEAD"
)
@click.option(
    "--start", help="Start of the commit range (exclusive)", default=None
)
@click.option(
    "--extra-revs",
    "-er",
    multiple=True,
    help="Add a list of additional revisions to the case-study"
)
@click.option(
    "--revs-per-year",
    type=int,
    default=0,
    help="Add this many revisions per year to the case-study."
)
@click.option(
    "--revs-year-sep",
    is_flag=True,
    help="Separate the revisions in different stages per year "
    "(when using \'--revs-per-year\')."
)
@click.option(
    "--num-rev", type=int, default=10, help="Number of revisions to select."
)
@click.option(
    "--ignore-blocked",
    is_flag=True,
    help="Ignore revisions that are marked as blocked."
)
def __casestudy_create_or_extend(
    paper_config_path: Path, distribution: str, version: int, end: str,
    start: str, project: str, **args: tp.Any
) -> None:
    """
    Generate a case study.

    PAPER_CONFIG_PATH: Path to paper_config folder (e.g., paper_configs/ase-17)
    """
    if not project and not args['git_path']:
        click.echo("need --project or --git-path", err=True)

    if project and not args['git_path']:
        args['git_path'] = str(get_local_project_git_path(project))
    if args['git_path'] and not project:
        project = Path(args['git_path']).stem.replace("-HEAD", "")

    get_cmap = create_lazy_commit_map_loader(project, None, end, start)
    cmap = get_cmap()

    args['extra_revs'] = list(args['extra_revs'])
    # Rewrite requested distribution with initialized object
    if distribution:
        sampling_method: tp.Optional[
            NormalSamplingMethod
        ] = NormalSamplingMethod.get_sampling_method_type(distribution)()
    else:
        sampling_method = None

    # Specify merge_stage as 0 for creating new case studies
    args['merge_stage'] = 0
    args['distribution'] = sampling_method
    case_study = generate_case_study(
        sampling_method, cmap, version, project, **args
    )
    store_case_study(case_study, Path(paper_config_path))


@main.command("package")
@click.argument("report_names", type=create_report_type_choice(), nargs=-1)
@click.option("-o", "--output", help="Output file")
@click.option(
    "--filter-regex",
    help="Provide a regex to only include case "
    "studies that match the filter.",
    type=str,
    default=".*"
)
def __casestudy_package(
    output: str, filter_regex: str, report_names: tp.List[str]
) -> None:
    """
    Case study packaging util.

    REPORT_NAMES: Provide report names to select which files are considered
    for packaging
    """
    output_path = Path(output)
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
            output_path, re.compile(filter_regex), report_names
        )
    else:
        click.echo(
            "--output has the wrong file type extension. "
            "Please do not provide any other file type extension than .zip",
            err=True
        )


@main.command("view")
@click.argument("report-type", type=create_report_type_choice())
@click.argument("project")
@click.argument("commit-hash", required=False)
@click.option(
    "--newest-only",
    is_flag=True,
    help="Only report the newest file for each matched commit hash"
)
def __casestudy_view(
    report_type: str, project: str, commit_hash: ShortCommitHash,
    newest_only: bool
) -> None:
    """
    View report files.

    REPORT_TYPE: Report type of the result files.
    PROJECT: Project to view result files for.
    COMMIT_HASH: Commit hash to view result files for.
    """
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


def __init_commit_hash(
    report_type: tp.Type[BaseReport], project: str, commit_hash: ShortCommitHash
) -> ShortCommitHash:
    if not commit_hash:
        # Ask the user to provide a commit hash
        print("No commit hash was provided.")
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
    return commit_hash


@main.group()
def cleanup() -> None:
    """Cleanup report files."""
    return


@cleanup.command("old")
def _remove_old_result_files() -> None:
    """Remove result files of wich a newer version exists."""
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


@cleanup.command("error")
def _remove_error_result_files() -> None:
    """Remove error result files."""
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
    """Remove result files based on a given regex filter."""
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


class CleanupType(Enum):
    OLD = 0
    ERROR = 1
    REGEX = 2


if __name__ == '__main__':
    main()
