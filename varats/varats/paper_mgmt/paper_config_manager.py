"""Module for interacting and managing paper configs and case studies, e.g.,
this modules provides functionality to visualize the status of case studies or
to package a whole paper config into a zip folder."""

import re
import typing as tp
from collections import defaultdict
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from plumbum import colors

import varats.paper_mgmt.paper_config as PC
from varats.experiment.experiment_util import VersionExperiment
from varats.mapping.commit_map import create_lazy_commit_map_loader
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import (
    get_revisions_status_for_case_study,
    get_newest_result_files_for_case_study,
)
from varats.report.report import FileStatusExtension, BaseReport, ReportFilename
from varats.revision.revisions import get_all_revisions_files
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import vara_cfg


def show_status_of_case_studies(
    experiment_type: tp.Type[VersionExperiment], filter_regex: str,
    short_status: bool, sort: bool, print_rev_list: bool, sep_stages: bool,
    print_legend: bool
) -> None:
    """
    Prints the status of all matching case studies to the console.

    Args:
        experiment_type: experiment type whose files will be considered
        filter_regex: applied to a ``name_version`` string for filtering the
                      amount of case studies to be shown
        short_status: print only a short version of the status information
        sort: sort the output order of the case studies
        print_rev_list: print a list of revisions for every case study
        sep_stages: print each stage separeted
        print_legend: print a legend for the different types
    """
    current_config = PC.get_paper_config()

    longest_cs_name = 0
    output_case_studies = []
    for case_study in sorted(
        current_config.get_all_case_studies(),
        key=lambda cs: (cs.project_name, cs.version)
    ):
        match = re.match(
            filter_regex, f"{case_study.project_name}_{case_study.version}"
        )
        if match is not None:
            output_case_studies.append(case_study)
            longest_cs_name = max(
                longest_cs_name,
                len(case_study.project_name) + len(str(case_study.version))
            )

    if print_legend:
        print(get_legend(True))

    total_status_occurrences: tp.DefaultDict[
        FileStatusExtension, tp.Set[ShortCommitHash]] = defaultdict(set)

    for case_study in output_case_studies:
        if print_rev_list:
            print(get_revision_list(case_study))
        elif short_status:
            print(
                get_short_status(
                    case_study, experiment_type, longest_cs_name, True,
                    total_status_occurrences
                )
            )
        else:
            print(
                get_status(
                    case_study, experiment_type, longest_cs_name, sep_stages,
                    sort, True, total_status_occurrences
                )
            )

    print(get_total_status(total_status_occurrences, longest_cs_name, True))


def get_revision_list(case_study: CaseStudy) -> str:
    """Returns a string with a list of revsion from the case-study, group by
    case- study stages.

    Args:
        case_study: to print revisions for

    Returns:
        formated string that lists all revisions
    """
    res_str = f"CS: {case_study.project_name}_{case_study.version}:\n"

    for idx, stage in enumerate(case_study.stages):
        res_str += f"  Stage {idx}\n"
        for rev in stage.revisions:
            res_str += f"    {rev}\n"

    return res_str


def get_result_files(
    result_file_type: tp.Type[BaseReport], project_name: str,
    commit_hash: ShortCommitHash, only_newest: bool
) -> tp.List[Path]:
    """
    Returns a list of result files that (partially) match the given commit hash.

    Args:
        result_file_type: the type of the result file
        project_name: target project
        commit_hash: the commit hash to search result files for
        only_newest: whether to include all result files, or only the newest;
                     if ``False``, result files for the same revision are sorted
                     descending by the file's mtime

    Returns:
        a list of matching result file paths; result files for the same revision
        are sorted descending by the file's mtime
    """

    def file_name_filter(file_name: str) -> bool:
        file_commit_hash = ReportFilename(file_name).commit_hash
        return not file_commit_hash == commit_hash

    return get_all_revisions_files(
        project_name, result_file_type, file_name_filter, only_newest
    )


def get_occurrences(
    status_occurrences: tp.DefaultDict[FileStatusExtension,
                                       tp.Set[ShortCommitHash]],
    use_color: bool = False
) -> str:
    """
    Returns a string with all status occurrences of a case study.

    Args:
        status_occurrences: mapping from all occurred status to a set of
                            revisions
        use_color: add color escape sequences for highlighting

    Returns:
        a string with all status occurrences of a case study
    """
    status = ""

    num_succ_rev = len(status_occurrences[FileStatusExtension.SUCCESS])
    num_rev = sum(map(len, status_occurrences.values()))

    color = None
    if use_color:
        if num_succ_rev == num_rev:
            color = colors.green
        elif num_succ_rev == 0:
            color = colors.red
        else:
            color = colors.orange3

    if color is not None:
        status += "(" + color[f"{num_succ_rev:3}/{num_rev}"] + ") processed "
    else:
        status += "(" + f"{num_succ_rev:3}/{num_rev}" + ") processed "

    status += "["
    for file_status in FileStatusExtension:
        if use_color:
            status += file_status.status_color[str(
                len(status_occurrences[file_status])
            )] + "/"
        else:
            status += str(len(status_occurrences[file_status])) + "/"

    status = status[:-1]
    status += "]"
    return status


def get_total_status(
    total_status_occurrences: tp.DefaultDict[FileStatusExtension,
                                             tp.Set[ShortCommitHash]],
    longest_cs_name: int,
    use_color: bool = False
) -> str:
    """
    Returns a status string showing the total amount of occurrences.

    Args:
        total_status_occurrences: mapping from all occured status to a set of
                                  all revisions (total amount of revisions)
        longest_cs_name: amount of chars that should be considered for
        use_color: add color escape sequences for highlighting

    Returns:
        a string with all status occurrences of all case studies
    """
    status = "-" * 80
    status += "\n"
    status += "Total: ".ljust(longest_cs_name, ' ')
    status += get_occurrences(total_status_occurrences, use_color)
    return status


def get_short_status(
    case_study: CaseStudy,
    experiment_type: tp.Type[VersionExperiment],
    longest_cs_name: int,
    use_color: bool = False,
    total_status_occurrences: tp.Optional[tp.DefaultDict[
        FileStatusExtension, tp.Set[ShortCommitHash]]] = None
) -> str:
    """
    Return a short string representation that describes the current status of
    the case study.

    Args:
        case_study: to print
        experiment_type: experiment type to print files for
        longest_cs_name: amount of chars that should be considered for
                         offsetting to allow case study name alignment
        use_color: add color escape sequences for highlighting
        total_status_occurrences: mapping from all occured status to a set of
                                  all revisions (total amount of revisions)

    Returns:
        a short string representation of a case study
    """
    status = f"CS: {case_study.project_name}_{case_study.version}: " + "".ljust(
        longest_cs_name -
        (len(case_study.project_name) + len(str(case_study.version))), ' '
    )

    status_occurrences: tp.DefaultDict[
        FileStatusExtension, tp.Set[ShortCommitHash]] = defaultdict(set)

    for tagged_rev in _combine_tagged_revs_for_experiment(
        case_study, experiment_type
    ):
        status_occurrences[tagged_rev[1]].add(tagged_rev[0])

    if total_status_occurrences is not None:
        for file_status, rev_set in status_occurrences.items():
            total_status_occurrences[file_status].update(rev_set)

    status += get_occurrences(status_occurrences, use_color)
    return status


def get_status(
    case_study: CaseStudy,
    experiment_type: tp.Type[VersionExperiment],
    longest_cs_name: int,
    sep_stages: bool,
    sort: bool,
    use_color: bool = False,
    total_status_occurrences: tp.Optional[tp.DefaultDict[
        FileStatusExtension, tp.Set[ShortCommitHash]]] = None
) -> str:
    """
    Return a string representation that describes the current status of the case
    study.

    Args:
        case_study: to print the status for
        experiment_type: experiment type to print files for
        longest_cs_name: amount of chars that should be considered for
        sep_stages: print each stage separeted
        sort: sort the output order of the case studies
        use_color: add color escape sequences for highlighting
        total_status_occurrences: mapping from all occured status to a set of
                                  all revisions (total amount of revisions)

    Returns:
        a full string representation of all case studies
    """
    status = get_short_status(
        case_study, experiment_type, longest_cs_name, use_color,
        total_status_occurrences
    ) + "\n"

    if sort:
        cmap = create_lazy_commit_map_loader(case_study.project_name)()

    def rev_time(rev: tp.Tuple[ShortCommitHash, FileStatusExtension]) -> int:
        return cmap.short_time_id(rev[0])

    if sep_stages:
        stages = case_study.stages
        for stage_num in range(0, case_study.num_stages):
            status += f"  Stage {stage_num}"
            stage_name = stages[stage_num].name
            if stage_name:
                status += f" ({stage_name})"
            status += "\n"
            tagged_revs = _combine_tagged_revs_for_experiment(
                case_study, experiment_type, stage_num
            )
            if sort:
                tagged_revs = sorted(tagged_revs, key=rev_time, reverse=True)
            for tagged_rev_state in tagged_revs:
                status += f"    {tagged_rev_state[0].hash} " \
                          f"[{tagged_rev_state[1].get_colored_status()}]\n"
    else:
        tagged_revs = list(
            dict.fromkeys(
                _combine_tagged_revs_for_experiment(
                    case_study, experiment_type
                )
            )
        )
        if sort:
            tagged_revs = sorted(tagged_revs, key=rev_time, reverse=True)
        for tagged_rev_state in tagged_revs:
            status += f"    {tagged_rev_state[0].hash} " \
                      f"[{tagged_rev_state[1].get_colored_status()}]\n"

    return status


def get_legend(use_color: bool = False) -> str:
    """
    Builds up a complete legend that explains all status numbers and their
    colors.

    Args:
        use_color: add color escape sequences for highlighting

    Returns:
        a legend to explain different status
    """
    legend_str = "CS: project_42: (Success / Total) processed ["

    for file_status in FileStatusExtension:
        if use_color:
            legend_str += file_status.get_colored_status() + "/"
        else:
            legend_str += file_status.nice_name() + "/"

    legend_str = legend_str[:-1]
    legend_str += "]\n"
    return legend_str


def package_paper_config(
    output_file: Path, cs_filter_regex: tp.Pattern[str],
    report_names: tp.List[tp.Type[BaseReport]]
) -> None:
    """
    Package all files from a paper config into a zip folder.

    Args:
        output_file: file to write to
        cs_filter_regex: applied to a ``name_version`` string for filtering the
                         case studies to be included in the zip archive
        report_names: list of report names that should be added
    """
    current_config = PC.get_paper_config()
    result_dir = Path(str(vara_cfg()['result_dir']))
    report_types = report_names if report_names else list(
        BaseReport.REPORT_TYPES.values()
    )

    files_to_store: tp.Set[Path] = set()
    for case_study in current_config.get_all_case_studies():
        match = re.match(
            cs_filter_regex, f"{case_study.project_name}_{case_study.version}"
        )
        if match is not None:
            for report_type in report_types:
                files_to_store.update(
                    get_newest_result_files_for_case_study(
                        case_study, result_dir, report_type
                    )
                )

    case_study_files_to_include: tp.List[Path] = []
    for cs_file in current_config.path.iterdir():
        match = re.match(cs_filter_regex, cs_file.name)
        if match is not None:
            case_study_files_to_include.append(cs_file)

    vara_root = Path(str(vara_cfg()['config_file'])).parent
    with ZipFile(
        output_file, "w", compression=ZIP_DEFLATED, compresslevel=9
    ) as pc_zip:
        for file_path in files_to_store:
            pc_zip.write(file_path.relative_to(vara_root))

        for case_study_file in case_study_files_to_include:
            pc_zip.write(case_study_file.relative_to(vara_root))


def _combine_tagged_revs_for_experiment(
    case_study: CaseStudy,
    experiment_type: tp.Type[VersionExperiment],
    stage_num: tp.Optional[int] = None
) -> tp.List[tp.Tuple[ShortCommitHash, FileStatusExtension]]:
    """
    Combines the tagged revision results from all report that are specified in
    the experiment.

    Args:
        case_study: to print
        experiment_type: experiment type to print files for

    Returns:
        combined tagged revision list
    """
    combined_tagged_revisions: tp.Dict[ShortCommitHash,
                                       FileStatusExtension] = {}
    for report in experiment_type.report_spec():
        if stage_num:
            tagged_revs = get_revisions_status_for_case_study(
                case_study, report, stage_num, experiment_type=experiment_type
            )
        else:
            tagged_revs = get_revisions_status_for_case_study(
                case_study, report, experiment_type=experiment_type
            )

        for tagged_rev in tagged_revs:
            if tagged_rev[0] in combined_tagged_revisions:
                combined_tagged_revisions[
                    tagged_rev[0]] = FileStatusExtension.combine(
                        combined_tagged_revisions[tagged_rev[0]], tagged_rev[1]
                    )
            else:
                combined_tagged_revisions[tagged_rev[0]] = tagged_rev[1]

    return list(combined_tagged_revisions.items())
