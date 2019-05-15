"""
Module for interacting with paper configs.
"""

import re

from varats.data.commit_report import CommitReport
from varats.settings import CFG
import varats.paper.paper_config as PC


def show_status_of_case_studies(filter_regex: str, short_status: bool):
    """
    Show the status of all matching case studies.
    """
    print("Searching with regex: ", filter_regex)

    # load paper config
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
                print(case_study.get_short_status(CommitReport))
            else:
                print(case_study.get_status(CommitReport))
