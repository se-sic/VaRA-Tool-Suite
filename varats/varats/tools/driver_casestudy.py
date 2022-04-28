"""Driver module for `vara-cs`."""

import logging
import os
import re
import typing as tp
from pathlib import Path

import click
import pygit2
from plumbum import FG, colors, local

from varats.base.sampling_method import NormalSamplingMethod
from varats.data.discover_reports import initialize_reports
from varats.data.reports.szz_report import SZZReport
from varats.experiment.experiment_util import VersionExperiment
from varats.mapping.commit_map import (
    create_lazy_commit_map_loader,
    generate_commit_map,
)
from varats.paper.case_study import (
    load_case_study_from_file,
    store_case_study,
    CaseStudy,
    CSStage,
)
from varats.paper_mgmt import paper_config_manager as PCM
from varats.paper_mgmt.case_study import (
    get_revisions_status_for_case_study,
    extend_with_distrib_sampling,
    extend_with_revs_per_year,
    extend_with_smooth_revs,
    extend_with_release_revs,
    extend_with_bug_commits,
    extend_with_extra_revs,
)
from varats.paper_mgmt.paper_config import get_paper_config
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator, PlotConfig, PlotGeneratorFailed
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
    add_cli_options,
)
from varats.ts_utils.click_param_types import (
    create_experiment_type_choice,
    create_report_type_choice,
    TypedChoice,
    EnumChoice,
    create_multi_case_study_choice,
)
from varats.utils.git_commands import pull_current_branch
from varats.utils.git_util import (
    get_initial_commit,
    is_commit_hash,
    get_commits_before_timestamp,
    ShortCommitHash,
    FullCommitHash,
)
from varats.utils.settings import vara_cfg

LOG = logging.getLogger(__name__)


def create_plot_type_choice() -> TypedChoice[tp.Type[Plot]]:
    initialize_plots()
    return TypedChoice(Plot.PLOTS)


@click.group()
@configuration_lookup_error_handler
def main() -> None:
    """Allow easier management of case studies."""
    initialize_cli_tool()
    initialize_projects()
    initialize_reports()


@main.command("status")
@click.argument("experiment_type", type=create_experiment_type_choice())
@click.option(
    "--filter-regex",
    help="Provide a regex to filter the shown case studies",
    default=".*"
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
    experiment_type: tp.Type[VersionExperiment], filter_regex: str, short: bool,
    list_revs: bool, with_stage: bool, sort_revs: bool, legend: bool,
    force_color: bool
) -> None:
    """
    Show status of current case study.

    EXPERIMENT-NAME: Provide a experiment name to select which files are
    considered for the status
    """
    if force_color:
        colors.use_color = True
    if short and list_revs:
        click.UsageError(
            "At most one argument of: --short, --list-revs can be used."
        )
    if short and with_stage:
        click.UsageError("At most one argument of: --short, --ws can be used.")
    PCM.show_status_of_case_studies(
        experiment_type, filter_regex, short, sort_revs, list_revs, with_stage,
        legend
    )


@main.group("gen")
@click.option("--project", "-p", required=True)
@click.option(
    "--override",
    "-or",
    is_flag=True,
    help="If a case study for the given project and version"
    " exists override it instead of extending it"
)
@click.option(
    "--merge-stage",
    help="Merge the new revision(s) into stage "
    "`n`; defaults to last stage.",
    type=str,
    default=None
)
@click.option(
    "--new-stage", is_flag=True, help="Add the new revision(s) to a new stage"
)
@click.option(
    "-v", "--version", type=int, default=0, help="Case study version."
)
@click.option(
    "--ignore-blocked/--allow-blocked",
    default=True,
    help="Ignore/Allow revisions that are marked as blocked. By default, "
    "blocked revisions will be ignored."
)
@click.option(
    "--update/--no-update",
    is_flag=True,
    default=True,
    help="Project repository will not be updated."
)
@click.pass_context
def __casestudy_gen(
    ctx: click.Context, project: str, override: bool, version: int,
    ignore_blocked: bool, merge_stage: tp.Optional[str], new_stage: bool,
    update: bool
) -> None:
    """Generate or extend a CaseStudy Sub commands can be chained to for example
    sample revisions but also add the latest."""
    ctx.ensure_object(dict)
    ctx.obj['project'] = project
    ctx.obj['ignore_blocked'] = ignore_blocked
    ctx.obj['version'] = version
    paper_config = vara_cfg()["paper_config"]["current_config"].value
    if not paper_config:
        click.echo(
            "You need to create a paper config first"
            " using vara-pc create"
        )
        return
    ctx.obj['path'] = Path(
        vara_cfg()["paper_config"]["folder"].value
    ) / (paper_config + f"/{project}_{version}.case_study")
    ctx.obj['git_path'] = get_local_project_git_path(project)
    if update:
        pull_current_branch(ctx.obj['git_path'])

    if override or not ctx.obj['path'].exists():
        case_study = CaseStudy(ctx.obj['project'], version)
        if merge_stage:
            case_study.insert_empty_stage(0)
            case_study.name_stage(0, merge_stage)
        ctx.obj["merge_stage"] = 0
    else:
        case_study = load_case_study_from_file(ctx.obj['path'])
        ctx.obj['custom_stage'] = bool(merge_stage)
        if merge_stage:
            if new_stage:
                stage_index = case_study.num_stages
                case_study.insert_empty_stage(stage_index)
                case_study.name_stage(stage_index, merge_stage)
            else:
                stage_index_opt = case_study \
                    .get_stage_index_by_name(merge_stage)
                if not stage_index_opt:
                    selected_stage = CSStage(merge_stage)

                    def set_merge_stage(stage: CSStage) -> None:
                        nonlocal selected_stage
                        selected_stage = stage

                    stage_choices = [selected_stage]
                    stage_choices.extend([
                        stage for stage in case_study.stages if stage.name
                    ])
                    cli_list_choice(
                        f"The given stage({merge_stage}) does not exist,"
                        f" do you want to create it or select an existing one",
                        stage_choices, lambda x: x.name
                        if x.name else "", set_merge_stage
                    )
                    if selected_stage.name == merge_stage:
                        stage_index = case_study.num_stages
                        case_study.insert_empty_stage(stage_index)
                        case_study.name_stage(stage_index, selected_stage.name)
                    else:
                        stage_index = case_study.stages.index(selected_stage)
                else:
                    stage_index = stage_index_opt
            ctx.obj['merge_stage'] = stage_index

        else:
            ctx.obj['merge_stage'] = max(case_study.num_stages, 0)
    ctx.obj['case_study'] = case_study


@__casestudy_gen.command("select_latest")
@click.pass_context
def __gen_latest(ctx: click.Context) -> None:
    """Add the latest revision of the project to the CS."""

    cmap = generate_commit_map(ctx.obj["git_path"])
    case_study: CaseStudy = ctx.obj['case_study']

    repo = pygit2.Repository(pygit2.discover_repository(ctx.obj["git_path"]))
    last_commit = FullCommitHash.from_pygit_commit(repo[repo.head.target])

    case_study.include_revisions([(last_commit, cmap.time_id(last_commit))])
    store_case_study(case_study, ctx.obj['path'])


@__casestudy_gen.command("select_specific")
@click.argument("revisions", nargs=-1)
@click.pass_context
def __gen_specific(ctx: click.Context, revisions: tp.List[str]) -> None:
    """
    Adds a list of specified revisions to the CS.

    Revisions: Revisions to add
    """
    cmap = create_lazy_commit_map_loader(
        ctx.obj['project'], None, 'HEAD', None
    )()
    extend_with_extra_revs(
        ctx.obj['case_study'], cmap, revisions, ctx.obj['merge_stage']
    )
    store_case_study(ctx.obj['case_study'], ctx.obj['path'])


@__casestudy_gen.command("select_sample")
@click.argument(
    "distribution",
    type=click.Choice([
        x.name() for x in NormalSamplingMethod.normal_sampling_method_types()
    ])
)
@click.option(
    "--end", help="End of the commit range (inclusive)", default="HEAD"
)
@click.option(
    "--start", help="Start of the commit range (exclusive)", default=None
)
@click.option(
    "--num-rev", type=int, default=10, help="Number of revisions to select."
)
@click.option(
    "--only-code-commits",
    is_flag=True,
    help="Only consider code changes when sampling."
)
@click.pass_context
def __gen_sample(
    ctx: click.Context, distribution: str, end: str, start: str, num_rev: int,
    only_code_commits: bool
) -> None:
    """
    Add revisions based on a sampling Distribution.

    Distribution: The sampling method to use
    """
    sampling_method: NormalSamplingMethod = NormalSamplingMethod \
        .get_sampling_method_type(
        distribution
    )()

    project_repo_path = get_local_project_git_path(ctx.obj['project'])
    if end != "HEAD" and not is_commit_hash(end):
        end = get_commits_before_timestamp(end, project_repo_path)[0].hash

    if start is not None and not is_commit_hash(start):
        commits_before = get_commits_before_timestamp(start, project_repo_path)
        if commits_before:
            start = commits_before[0].hash
        else:
            start = get_initial_commit(project_repo_path).hash

    cmap = create_lazy_commit_map_loader(ctx.obj['project'], None, end, start)()
    extend_with_distrib_sampling(
        ctx.obj['case_study'], cmap, sampling_method, ctx.obj['merge_stage'],
        num_rev, ctx.obj['ignore_blocked'], only_code_commits
    )
    store_case_study(ctx.obj['case_study'], ctx.obj['path'])


@__casestudy_gen.command("select_revs-per-year")
@click.argument("revs-per-year", type=int)
@click.option(
    "--separate", is_flag=True, help="Separate years into different Stages"
)
@click.pass_context
def __gen_per_year(
    ctx: click.Context, revs_per_year: int, separate: bool
) -> None:
    """
    Add a number of revisions per year.

    revs-per-year: number of revisions to generate per year
    """
    cmap = create_lazy_commit_map_loader(
        ctx.obj['project'], None, 'HEAD', None
    )()
    extend_with_revs_per_year(
        ctx.obj['case_study'], cmap, ctx.obj['merge_stage'],
        ctx.obj['ignore_blocked'], ctx.obj['git_path'], revs_per_year, separate
    )
    store_case_study(ctx.obj['case_study'], ctx.obj['path'])


class SmoothPlotCLI(click.MultiCommand):
    """Command factory for plots."""

    def __init__(self, **attrs: tp.Any):
        initialize_plots()
        super().__init__(**attrs)

    def list_commands(self, ctx: click.Context) -> tp.List[str]:
        return list(PlotGenerator.GENERATORS.keys())

    def get_command(self, ctx: click.Context,
                    cmd_name: str) -> tp.Optional[click.Command]:

        generator_cls = PlotGenerator.GENERATORS[cmd_name]

        @click.pass_context
        def command_template(context: click.Context, **kwargs: tp.Any) -> None:
            # extract common arguments and plot config from context
            plot_config: PlotConfig = PlotConfig(False)
            try:
                generator_instance = generator_cls(plot_config, **kwargs)
                plots = generator_instance.generate()
                plot = plots[0]
                if len(plots) > 1:

                    def set_plot(selected_plot: Plot) -> None:
                        nonlocal plot
                        plot = selected_plot

                    cli_list_choice(
                        "The given plot generator creates multiple plots"
                        " please select one:", plots, lambda p: p.name, set_plot
                    )
                cmap = create_lazy_commit_map_loader(
                    context.obj['project'], None, 'HEAD', None
                )()
                extend_with_smooth_revs(
                    context.obj['case_study'], cmap,
                    context.obj['boundary_gradient'],
                    context.obj['ignore_blocked'], plot,
                    context.obj['merge_stage']
                )
                store_case_study(context.obj['case_study'], context.obj['path'])
            except PlotGeneratorFailed as ex:
                print(
                    f"Failed to create plot generator {generator_cls.NAME}: "
                    f"{ex.message}"
                )

        # return command wrapped with options specified in the generator class
        command_definition = add_cli_options(
            command_template, *generator_cls.OPTIONS
        )
        return click.command(cmd_name)(command_definition)


@__casestudy_gen.command("select_plot", cls=SmoothPlotCLI)
@click.option(
    "--boundary-gradient",
    type=int,
    default=5,
    help="Maximal expected gradient in percent between " +
    "two revisions, e.g., 5 for 5%%"
)
@click.pass_context
def __gen_smooth_plot(ctx: click.Context, boundary_gradient: int) -> None:
    """
    Generate revisions based on a plot.

    plot_type: Plot to calculate new revisions from.
    """
    ctx.obj['boundary_gradient'] = boundary_gradient


@__casestudy_gen.command("select_release")
@click.argument("release_type", type=EnumChoice(ReleaseType, False))
@click.pass_context
def __gen_release(ctx: click.Context, release_type: ReleaseType) -> None:
    """
    Extend a case study with revisions marked as a release. This relies on the
    project to determine appropriate revisions.

    release_type: Release type to consider
    """
    cmap = create_lazy_commit_map_loader(
        ctx.obj['project'], None, 'HEAD', None
    )()
    extend_with_release_revs(
        ctx.obj['case_study'], cmap, release_type, ctx.obj['ignore_blocked'],
        ctx.obj['merge_stage']
    )
    store_case_study(ctx.obj['case_study'], ctx.obj['path'])


@__casestudy_gen.command("select_bug")
@click.argument(
    "report_type",
    type=TypedChoice({
        k: v
        for (k, v) in BaseReport.REPORT_TYPES.items()
        if isinstance(v, SZZReport)
    })
)
@click.pass_context
def __gen_bug_commits(
    ctx: click.Context, report_type: tp.Type['BaseReport']
) -> None:
    """
    Extend a case study with revisions that either introduced or fixed a bug as
    determined by the given SZZ tool.

    REPORT_TYPE: report to use for determining bug regions
    """
    cmap = create_lazy_commit_map_loader(
        ctx.obj['project'], None, 'HEAD', None
    )()
    extend_with_bug_commits(
        ctx.obj['case_study'], cmap, report_type, ctx.obj['merge_stage'],
        ctx.obj['ignore_blocked']
    )
    store_case_study(ctx.obj['case_study'], ctx.obj['path'])


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
    output: str, filter_regex: str, report_names: tp.List[tp.Type[BaseReport]]
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
@click.option(
    "--report-type",
    type=create_report_type_choice(),
    required=True,
    help="Report type of the result files."
)
@click.option(
    "--project", required=True, help="Project to view result files for."
)
@click.option("--commit-hash", help="Commit hash to view result files for.")
@click.option(
    "--newest-only",
    is_flag=True,
    help="Only report the newest file for each matched commit hash"
)
def __casestudy_view(
    report_type: tp.Type[BaseReport], project: str,
    commit_hash: ShortCommitHash, newest_only: bool
) -> None:
    """View report files."""
    try:
        commit_hash = __init_commit_hash(report_type, project, commit_hash)
    except LookupError:
        return

    result_files = PCM.get_result_files(
        report_type, project, commit_hash, newest_only
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

    editor_name = "vim"  # set's default editor

    if "EDITOR" in local.env:
        editor_name = local.env["EDITOR"]

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

        max_num_hashes = 20
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
@click.option(
    "--case-studies",
    "-cs",
    type=create_multi_case_study_choice(),
    default='all',
    help="Only remove reports for revisions from "
    "these case studies, defaults to all case "
    "studies from the current paper config"
)
@click.option(
    "--experiment",
    "-exp",
    type=create_experiment_type_choice(),
    help="Only remove reports that belong to the given experiment"
)
@click.option(
    "--report",
    type=create_report_type_choice(),
    help="Only remove reports from the given type."
)
@click.pass_context
def cleanup(
    ctx: click.Context, case_studies: tp.List[CaseStudy],
    experiment: tp.Optional[VersionExperiment], report: tp.Optional[BaseReport]
) -> None:
    """
    Cleanup report files.

    If both --experiment and --report the report file has to belong to both
    """

    ctx.ensure_object(dict)
    ctx.obj["case_studies"] = case_studies
    ctx.obj["experiment"] = experiment
    ctx.obj["report"] = report


@cleanup.command("all")
@click.option(
    "--error", is_flag=True, help="remove only reports from failed experiments"
)
@click.pass_context
def _remove_all_result_files(ctx: click.Context, error: bool) -> None:
    """Remove all report files of the current paper_config."""
    result_folders = _find_result_dir_paths_of_projects(ctx.obj["case_studies"])
    for folder in result_folders:
        for res_file in folder.iterdir():
            report_file = ReportFilename(res_file.name)
            if not report_file.is_result_file():
                continue
            if ctx.obj["experiment"] and not ctx.obj[
                "experiment"].file_belongs_to_experiment(res_file.name):
                continue
            if ctx.obj["report"] and not ctx.obj[
                "report"].is_correct_report_type(res_file.name):
                continue

            commit_hash = report_file.commit_hash
            if any(
                list(
                    case_study.has_revision(commit_hash)
                    for case_study in ctx.obj["case_studies"]
                )
            ):
                if error and not (
                    report_file.has_status_compileerror() or
                    report_file.has_status_failed()
                ):
                    continue
                res_file.unlink()


@cleanup.command("old")
@click.pass_context
def _remove_old_result_files(ctx: click.Context) -> None:
    """Remove result files of wich a newer version exists."""
    result_dir = Path(str(vara_cfg()['result_dir']))
    for case_study in ctx.obj['case_studies']:
        old_files: tp.List[Path] = []
        newer_files: tp.Dict[ShortCommitHash, Path] = {}
        result_dir_cs = result_dir / case_study.project_name
        if not result_dir_cs.exists():
            continue
        for opt_res_file in result_dir_cs.iterdir():
            report_file = ReportFilename(opt_res_file.name)
            if not report_file.is_result_file():
                continue
            if ctx.obj["experiment"] and not ctx.obj[
                "experiment"].file_belongs_to_experiment(opt_res_file.name):
                continue
            if ctx.obj["report"] and not ctx.obj[
                "report"].is_correct_report_type(opt_res_file.name):
                continue

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
                file.unlink()


@cleanup.command("regex")
@click.option(
    "--filter-regex",
    "-f",
    "regex_filter",
    prompt="Specify a regex for the filenames to delete",
    type=str
)
@click.option(
    "--silent", help="Hide the output of the matching filenames", is_flag=True
)
@click.pass_context
def _remove_result_files_by_regex(
    ctx: click.Context, regex_filter: str, silent: bool
) -> None:
    """
    Remove result files based on a given regex filter.

    Ignores experiment and report filter given to the main command
    """
    result_dir_paths = _find_result_dir_paths_of_projects(
        ctx.obj["case_studies"]
    )
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
        if not silent:
            for file_name in files_to_delete:
                print(f"{file_name}")
        print(
            f"Found {len(files_to_delete)} matching"
            "result files in {result_dir_path}:"
        )

        try:
            if cli_yn_choice("Do you want to delete these files", "n"):
                for file_name in files_to_delete:
                    file = Path(result_dir_path / file_name)
                    if file.exists():
                        file.unlink()
        except EOFError:
            continue


def _find_result_dir_paths_of_projects(case_studies: tp.List[CaseStudy]) -> \
        tp.List[Path]:
    result_dir_path = Path(vara_cfg()["result_dir"].value)
    existing_paper_config_result_dir_paths = []
    project_names = [cs.project_name for cs in case_studies]
    for project_name in project_names:
        path = Path(result_dir_path / project_name)
        if Path.exists(path):
            existing_paper_config_result_dir_paths.append(path)

    return existing_paper_config_result_dir_paths


if __name__ == '__main__':
    main()
