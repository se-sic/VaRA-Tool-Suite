"""
Module for handling the state of project revisions in VaRA.
"""

from collections import defaultdict
from pathlib import Path
from typing import Dict

from varats.settings import CFG


def __get_result_files_dict(project_name: str, result_file_type) -> Dict:
    """
    Returns a dict that maps the commit_hash to a list of all result files for that commit.

    Args:
        project_name: target project
        result_file_type: the type of the result file
    """
    res_dir = Path("{result_folder}/{project_name}/".format(
        result_folder=CFG["result_dir"], project_name=project_name))

    result_files = defaultdict(list) # maps commit hash -> list of res files (success or fail)
    if res_dir.exists():
        for res_file in res_dir.iterdir():
            if not str(res_file.stem).startswith("{}-".format(project_name)):
                continue
            match = result_file_type.FILE_STEM_REGEX.search(res_file.stem)
            if match:
                result_files[match.group("file_commit_hash")].append(res_file)

    return result_files


def get_proccessed_revisions(project_name: str, result_file_type) -> [str]:
    """
    Calculates a list of revisions of a project that have already
    been processed successfully.

    Args:
        project_name: target project
        result_file_type: the type of the result file
    """
    processed_revisions = []

    result_files = __get_result_files_dict(project_name, result_file_type)
    for _, value in result_files.items():
        newest_res_file = max(value, key=lambda x: Path(x).stat().st_mtime)
        match = result_file_type.FILE_NAME_SUCCESS_REGEX.search(newest_res_file.name)
        if match:
            processed_revisions.append(match.group("file_commit_hash"))

    return processed_revisions


def get_failed_revisions(project_name: str, result_file_type) -> [str]:
    """
    Calculates a list of revisions of a project that have failed.

    Args:
        project_name: target project
        result_file_type: the type of the result file
    """
    failed_revisions = []

    result_files = __get_result_files_dict(project_name, result_file_type)
    for _, value in result_files.items():
        newest_res_file = max(value, key=lambda x: Path(x).stat().st_mtime)
        match = result_file_type.FILE_NAME_FAILED_REGEX.search(newest_res_file.name)
        if match:
            failed_revisions.append(match.group("file_commit_hash"))

    return failed_revisions
