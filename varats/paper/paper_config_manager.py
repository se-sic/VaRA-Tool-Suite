"""
Module for interacting with paper configs.
"""

import typing as tp
import re
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from plumbum import colors

from varats.data.report import FileStatusExtension, MetaReport
from varats.data.reports.commit_report import CommitReport
from varats.paper.case_study import (CaseStudy,
                                     get_newest_result_files_for_case_study)
from varats.settings import CFG
import varats.paper.paper_config as PC


def show_status_of_case_studies(report_name: str, filter_regex: str,
                                short_status: bool, print_rev_list: bool,
                                sep_stages: bool, print_legend: bool) -> None:
    """
    Show the status of all matching case studies.
    """
    PC.load_paper_config(
        Path(
            str(CFG["paper_config"]["folder"]) + "/" +
            str(CFG["paper_config"]["current_config"])))

    current_config = PC.get_paper_config()

    longest_cs_name = 0
    output_case_studies = []
    for case_study in sorted(
            current_config.get_all_case_studies(),
            key=lambda cs: (cs.project_name, cs.version)):
        match = re.match(
            filter_regex, "{name}_{version}".format(
                name=case_study.project_name, version=case_study.version))
        if match is not None:
            output_case_studies.append(case_study)
            longest_cs_name = max(
                longest_cs_name,
                len(case_study.project_name) + len(str(case_study.version)))

    if print_legend:
        print(get_legend(True))

    report_type = MetaReport.REPORT_TYPES[report_name]

    for case_study in output_case_studies:
        if print_rev_list:
            print(get_revision_list(case_study))
        elif short_status:
            print(
                get_short_status(case_study, report_type, longest_cs_name,
                                 True))
        else:
            print(
                get_status(case_study, report_type, longest_cs_name,
                           sep_stages, True))


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


def get_short_status(case_study: CaseStudy,
                     result_file_type: MetaReport,
                     longest_cs_name: int,
                     use_color: bool = False) -> str:
    """
    Return a string representation that describes the current status of
    the case study.
    """
    status = "CS: {project}_{version}: ".format(
        project=case_study.project_name,
        version=case_study.version) + "".ljust(
            longest_cs_name -
            (len(case_study.project_name) + len(str(case_study.version))), ' ')

    status_occurrences: tp.DefaultDict[FileStatusExtension, int] = defaultdict(
        int)
    for tagged_rev in case_study.get_revisions_status(result_file_type):
        status_occurrences[tagged_rev[1]] += 1

    num_rev = len(set(case_study.revisions))

    num_succ_rev = status_occurrences[FileStatusExtension.Success]

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
                status_occurrences[file_status])] + "/"
        else:
            status += str(status_occurrences[file_status]) + "/"

    status = status[:-1]
    status += "]"

    return status


def get_status(case_study: CaseStudy,
               result_file_type: MetaReport,
               longest_cs_name: int,
               sep_stages: bool,
               use_color: bool = False) -> str:
    """
    Return a string representation that describes the current status of
    the case study.
    """
    status = get_short_status(case_study, result_file_type, longest_cs_name,
                              use_color) + "\n"

    if sep_stages:
        for stage_num in range(0, case_study.num_stages):
            status += "  Stage {idx}\n".format(idx=stage_num)
            for tagged_rev_state in case_study.get_revisions_status(
                    result_file_type, stage_num):
                status += "    {rev} [{status}]\n".format(
                    rev=tagged_rev_state[0],
                    status=tagged_rev_state[1].get_colored_status())
    else:
        for tagged_rev_state in list(
                dict.fromkeys(
                    case_study.get_revisions_status(result_file_type))):
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


def package_paper_config(output_file: Path,
                         cs_filter_regex: tp.Pattern[str]) -> None:
    """
    Package all files from a paper config into a zip folder.
    """
    cs_folder = Path(
        str(CFG["paper_config"]["folder"]) + "/" +
        str(CFG["paper_config"]["current_config"]))
    result_dir = Path(str(CFG['result_dir']))

    PC.load_paper_config(cs_folder)
    current_config = PC.get_paper_config()

    files_to_store: tp.Set[Path] = set()
    for case_study in current_config.get_all_case_studies():
        match = re.match(
            cs_filter_regex, "{name}_{version}".format(
                name=case_study.project_name, version=case_study.version))
        if match is not None:
            files_to_store.update(
                get_newest_result_files_for_case_study(case_study, result_dir,
                                                       CommitReport))

    case_study_files_to_include: tp.List[Path] = []
    for cs_file in cs_folder.iterdir():
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
