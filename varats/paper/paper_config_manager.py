"""
Module for interacting with paper configs.
"""

import typing as tp
import re
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from plumbum import colors
from varats.tools.commit_map import create_lazy_commit_map_loader

from varats.data.report import FileStatusExtension, MetaReport
from varats.data.reports.commit_report import CommitReport
from varats.paper.case_study import (CaseStudy,
                                     get_newest_result_files_for_case_study)
from varats.settings import CFG
import varats.paper.paper_config as PC


def show_status_of_case_studies(report_name: str, filter_regex: str,
                                short_status: bool, sort: bool,
                                print_rev_list: bool, sep_stages: bool,
                                print_legend: bool) -> None:
    """
    Show the status of all matching case studies.
    """
    current_config = PC.get_paper_config()

    longest_cs_name = 0
    output_case_studies = []
    for case_study in sorted(current_config.get_all_case_studies(),
                             key=lambda cs: (cs.project_name, cs.version)):
        match = re.match(
            filter_regex,
            "{name}_{version}".format(name=case_study.project_name,
                                      version=case_study.version))
        if match is not None:
            output_case_studies.append(case_study)
            longest_cs_name = max(
                longest_cs_name,
                len(case_study.project_name) + len(str(case_study.version)))

    if print_legend:
        print(get_legend(True))

    report_type = MetaReport.REPORT_TYPES[report_name]
    total_status_occurrences: tp.DefaultDict[FileStatusExtension, tp.
                                             Set[str]] = defaultdict(set)

    for case_study in output_case_studies:
        if print_rev_list:
            print(get_revision_list(case_study))
        elif short_status:
            print(
                get_short_status(case_study, report_type, longest_cs_name, True,
                                 total_status_occurrences))
        else:
            print(
                get_status(case_study, report_type, longest_cs_name, sep_stages,
                           sort, True, total_status_occurrences))

    print(get_total_status(total_status_occurrences, longest_cs_name, True))


def get_revision_list(case_study: CaseStudy) -> str:
    """
    Returns a string with a list of revsion from the case-study,
    group by case-study stages.
    """
    res_str = "CS: {project}_{version}:\n".format(
        project=case_study.project_name, version=case_study.version)

    for idx, stage in enumerate(case_study.stages):
        res_str += "  Stage {idx}\n".format(idx=idx)
        for rev in stage.revisions:
            res_str += "    {rev}\n".format(rev=rev)

    return res_str


def get_occurrences(
        status_occurrences: tp.DefaultDict[FileStatusExtension, tp.Set[str]],
        use_color: bool = False) -> str:
    """
    Returns a string with all status occurrences.
    """
    status = ""

    num_succ_rev = len(status_occurrences[FileStatusExtension.Success])
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
        status += "(" + color["{processed:3}/{total}".format(
            processed=num_succ_rev, total=num_rev)] + ") processed "
    else:
        status += "(" + "{processed:3}/{total}".format(
            processed=num_succ_rev, total=num_rev) + ") processed "

    status += "["
    for file_status in FileStatusExtension:
        if use_color:
            status += file_status.status_color[str(
                len(status_occurrences[file_status]))] + "/"
        else:
            status += str(len(status_occurrences[file_status])) + "/"

    status = status[:-1]
    status += "]"
    return status


def get_total_status(total_status_occurrences: tp.
                     DefaultDict[FileStatusExtension, tp.Set[str]],
                     longest_cs_name: int,
                     use_color: bool = False) -> str:
    """
    Returns a status string showing the total mount of occurrences.
    """
    status = "-" * 80
    status += "\n"
    status += "Total: ".ljust(longest_cs_name, ' ')
    status += get_occurrences(total_status_occurrences, use_color)
    return status


def get_short_status(
        case_study: CaseStudy,
        result_file_type: MetaReport,
        longest_cs_name: int,
        use_color: bool = False,
        total_status_occurrences: tp.Optional[
            tp.DefaultDict[FileStatusExtension, tp.Set[str]]] = None) -> str:
    """
    Return a string representation that describes the current status of
    the case study.
    """
    status = "CS: {project}_{version}: ".format(
        project=case_study.project_name, version=case_study.version) + "".ljust(
            longest_cs_name -
            (len(case_study.project_name) + len(str(case_study.version))), ' ')

    status_occurrences: tp.DefaultDict[FileStatusExtension, tp.
                                       Set[str]] = defaultdict(set)
    for tagged_rev in case_study.get_revisions_status(result_file_type):
        status_occurrences[tagged_rev[1]].add(tagged_rev[0])

    if total_status_occurrences is not None:
        for file_status, rev_set in status_occurrences.items():
            total_status_occurrences[file_status].update(rev_set)

    status += get_occurrences(status_occurrences, use_color)
    return status


def get_status(case_study: CaseStudy,
               result_file_type: MetaReport,
               longest_cs_name: int,
               sep_stages: bool,
               sort: bool,
               use_color: bool = False,
               total_status_occurrences: tp.Optional[
                   tp.DefaultDict[FileStatusExtension, tp.Set[str]]] = None
              ) -> str:
    """
    Return a string representation that describes the current status of
    the case study.
    """
    status = get_short_status(case_study, result_file_type, longest_cs_name,
                              use_color, total_status_occurrences) + "\n"

    if sort:
        cmap = create_lazy_commit_map_loader(case_study.project_name)()

    def rev_time(rev: tp.Tuple[str, FileStatusExtension]) -> int:
        return cmap.short_time_id(rev[0])

    if sep_stages:
        stages = case_study.stages
        for stage_num in range(0, case_study.num_stages):
            status += "  Stage {idx}".format(idx=stage_num)
            stage_name = stages[stage_num].name
            if stage_name:
                status += " ({})".format(stage_name)
            status += "\n"
            tagged_revs = case_study.get_revisions_status(
                result_file_type, stage_num)
            if sort:
                tagged_revs = sorted(tagged_revs, key=rev_time, reverse=True)
            for tagged_rev_state in tagged_revs:
                status += "    {rev} [{status}]\n".format(
                    rev=tagged_rev_state[0],
                    status=tagged_rev_state[1].get_colored_status())
    else:
        tagged_revs = list(
            dict.fromkeys(case_study.get_revisions_status(result_file_type)))
        if sort:
            tagged_revs = sorted(tagged_revs, key=rev_time, reverse=True)
        for tagged_rev_state in tagged_revs:
            status += "    {rev} [{status}]\n".format(
                rev=tagged_rev_state[0],
                status=tagged_rev_state[1].get_colored_status())

    return status


def get_legend(use_color: bool = False) -> str:
    """ Return a formated legend that explains all status numbers. """
    legend_str = "CS: project_42: (Success / Total) processed ["

    for file_status in FileStatusExtension:
        if use_color:
            legend_str += file_status.status_color[file_status.name] + "/"
        else:
            legend_str += file_status.name + "/"

    legend_str = legend_str[:-1]
    legend_str += "]\n"
    return legend_str


def package_paper_config(output_file: Path, cs_filter_regex: tp.Pattern[str],
                         report_names: tp.List[str]) -> None:
    """
    Package all files from a paper config into a zip folder.
    """
    current_config = PC.get_paper_config()
    result_dir = Path(str(CFG['result_dir']))
    report_types = [
        MetaReport.REPORT_TYPES[report_name] for report_name in report_names
    ] if report_names else [x for x in MetaReport.REPORT_TYPES.values()]

    files_to_store: tp.Set[Path] = set()
    for case_study in current_config.get_all_case_studies():
        match = re.match(
            cs_filter_regex,
            "{name}_{version}".format(name=case_study.project_name,
                                      version=case_study.version))
        if match is not None:
            for report_type in report_types:
                files_to_store.update(
                    get_newest_result_files_for_case_study(
                        case_study, result_dir, report_type))

    case_study_files_to_include: tp.List[Path] = []
    for cs_file in current_config.path.iterdir():
        match = re.match(cs_filter_regex, cs_file.name)
        if match is not None:
            case_study_files_to_include.append(cs_file)

    vara_root = Path(str(CFG['config_file'])).parent
    # TODO(python3.7): add ZipFile(compresslevel=9)
    with ZipFile(output_file, "w", compression=ZIP_DEFLATED) as pc_zip:
        for file_path in files_to_store:
            pc_zip.write(file_path.relative_to(vara_root))

        for case_study_file in case_study_files_to_include:
            pc_zip.write(case_study_file.relative_to(vara_root))
