"""
Module for interacting with paper configs.
"""

import re

from plumbum import colors

from varats.data.commit_report import CommitReport
from varats.settings import CFG
import varats.paper.paper_config as PC


def show_status_of_case_studies(filter_regex: str, short_status: bool):
    """
    Show the status of all matching case studies.
    """
    PC.load_paper_config(
        str(CFG["paper_config"]["folder"]) + "/" +
        str(CFG["paper_config"]["current_config"]))

    current_config = PC.get_paper_config()

    for case_study in sorted(
            current_config.get_all_case_studies(),
            key=lambda cs: (cs.project_name, cs.version)):
        match = re.match(
            filter_regex, "{name}_{version}".format(
                name=case_study.project_name, version=case_study.version))
        if match is not None:
            if short_status:
                print(get_short_status(case_study, CommitReport, True))
            else:
                print(get_status(case_study, CommitReport, True))


def get_short_status(case_study, result_file_type, use_color=False):
    """
    Return a string representation that describes the current status of
    the case study.
    """

    processed_revisions = case_study.processed_revisions(result_file_type)

    status = "CS: {project}_{version}: ".format(
        project=case_study.project_name, version=case_study.version)

    num_p_rev = len(processed_revisions)
    num_rev = len(case_study.revisions)

    color = None
    if use_color:
        if num_p_rev == num_rev:
            color = colors.green
        elif num_p_rev == 0:
            color = colors.red
        else:
            color = colors.orange3

    if color is not None:
        status += "(" + color["{processed}/{total}".format(
            processed=num_p_rev, total=num_rev)] + ") processed"
    else:
        status += "({processed}/{total}) processed".format(
            processed=num_p_rev, total=num_rev)

    return status


def get_status(case_study, result_file_type, use_color=False):
    """
    Return a string representation that describes the current status of
    the case study.
    """
    status = get_short_status(case_study, result_file_type, use_color) + "\n"

    def color_rev_state(rev_state):
        if use_color:
            return colors.green[
                rev_state] if rev_state == "OK" else colors.red[rev_state]
        else:
            return rev_state

    for rev_state in case_study.get_revisions_status(result_file_type):
        status += "    {rev} [{status:7s}]\n".format(
            rev=rev_state[0], status=color_rev_state(rev_state[1]))
    return status
