"""
Module for interacting with paper configs.
"""

import typing as tp
import re
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from plumbum import colors

from varats.data.commit_report import CommitReport
from varats.paper.case_study import (CaseStudy,
                                     get_newest_result_files_for_case_study)
from varats.settings import CFG
import varats.paper.paper_config as PC


def show_status_of_case_studies(filter_regex: str, short_status: bool,
                                print_rev_list: bool,
                                sep_stages: bool) -> None:
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

    for case_study in output_case_studies:
        if print_rev_list:
            print(get_revision_list(case_study))
        elif short_status:
            print(
                get_short_status(case_study, CommitReport, longest_cs_name,
                                 True))
        else:
            print(
                get_status(case_study, CommitReport, longest_cs_name,
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
                     result_file_type: tp.Type[CommitReport],
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

    num_p_rev = len(set(case_study.processed_revisions(result_file_type)))
    num_f_rev = len(set(case_study.failed_revisions(result_file_type)))
    num_rev = len(set(case_study.revisions))

    color = None
    if use_color:
        if num_p_rev == num_rev:
            color = colors.green
        elif num_p_rev == 0:
            color = colors.red
        else:
            color = colors.orange3

    if color is not None:
        status += "(" + color["{processed:3}/{total}".format(
            processed=num_p_rev, total=num_rev)] + ") processed "
        status += "[" + colors.red[str(num_f_rev)] + "/" + colors.orange3[str(
            num_rev - (num_f_rev + num_p_rev))] + "/" + colors.green[str(
                num_p_rev)] + "]"
    else:
        status += "({processed:3}/{total}) processed ".format(
            processed=num_p_rev, total=num_rev)
        status += "[{fail_rev}/{miss_rev}/{good_rev}]".format(
            fail_rev=num_f_rev,
            miss_rev=(num_rev - (num_f_rev + num_p_rev)),
            good_rev=num_p_rev)

    return status


def get_status(case_study: CaseStudy,
               result_file_type: tp.Type[CommitReport],
               longest_cs_name: int,
               sep_stages: bool,
               use_color: bool = False) -> str:
    """
    Return a string representation that describes the current status of
    the case study.
    """
    status = get_short_status(case_study, result_file_type, longest_cs_name,
                              use_color) + "\n"

    def color_rev_state(rev_state: str) -> str:
        if use_color:
            if rev_state == "OK":
                return tp.cast(str, colors.green[rev_state])
            if rev_state == "Failed":
                return tp.cast(str, colors.red[rev_state])
            return tp.cast(str, colors.orange3[rev_state])

        return rev_state

    if sep_stages:
        for stage_num in range(0, case_study.num_stages):
            status += "  Stage {idx}\n".format(idx=stage_num)
            for rev_state in case_study.get_revisions_status(
                    result_file_type, stage_num):
                status += "    {rev} [{status}]\n".format(
                    rev=rev_state[0], status=color_rev_state(rev_state[1]))
    else:
        for rev_state in list(
                dict.fromkeys(
                    case_study.get_revisions_status(result_file_type))):
            status += "    {rev} [{status}]\n".format(
                rev=rev_state[0], status=color_rev_state(rev_state[1]))

    return status


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
