"""
Module for handling the state of project revisions in VaRA.
"""

import typing as tp
from collections import defaultdict
from pathlib import Path

from varats.settings import CFG
from varats.data.report import MetaReport, FileStatusExtension


def __get_result_files_dict(project_name: str, result_file_type: MetaReport
                            ) -> tp.Dict[str, tp.List[Path]]:
    """
    Returns a dict that maps the commit_hash to a list of all result files for
    that commit.

    Args:
        project_name: target project
        result_file_type: the type of the result file
    """
    res_dir = Path("{result_folder}/{project_name}/".format(
        result_folder=CFG["result_dir"], project_name=project_name))

    result_files: tp.DefaultDict[str, tp.List[Path]] = defaultdict(
        list)  # maps commit hash -> list of res files (success or fail)
    if res_dir.exists():
        for res_file in res_dir.iterdir():
            if result_file_type.is_result_file(res_file.name):
                commit_hash = result_file_type.get_commit_hash_from_result_file(
                    res_file.name)
                result_files[commit_hash].append(res_file)

    return result_files


def get_processed_revisions(project_name: str,
                            result_file_type: MetaReport) -> tp.List[str]:
    """
    Calculates a list of revisions of a project that have already
    been processed successfully.

    Args:
        project_name: target project
        result_file_type: the type of the result file
    """
    processed_revisions = []

    result_files = __get_result_files_dict(project_name, result_file_type)
    for commit_hash, value in result_files.items():
        newest_res_file = max(value, key=lambda x: Path(x).stat().st_mtime)
        if result_file_type.is_result_file_success(newest_res_file.name):
            processed_revisions.append(commit_hash)

    return processed_revisions


def get_failed_revisions(project_name: str,
                         result_file_type: MetaReport) -> tp.List[str]:
    """
    Calculates a list of revisions of a project that have failed.

    Args:
        project_name: target project
        result_file_type: the type of the result file
    """
    failed_revisions = []

    result_files = __get_result_files_dict(project_name, result_file_type)
    for commit_hash, value in result_files.items():
        newest_res_file = max(value, key=lambda x: Path(x).stat().st_mtime)
        if result_file_type.is_result_file_failed(newest_res_file.name):
            failed_revisions.append(commit_hash)

    return failed_revisions


def get_tagged_revisions(project_name: str, result_file_type: MetaReport
                         ) -> tp.List[tp.Tuple[str, FileStatusExtension]]:
    """
    Calculates a list of revisions of a project tagged with the file status.
    If two files exists the newest is considered for detecting the status.

    Args:
        project_name: target project
        result_file_type: the type of the result file
    """
    revisions = []

    result_files = __get_result_files_dict(project_name, result_file_type)
    for commit_hash, file_list in result_files.items():
        newest_res_file = max(file_list, key=lambda x: x.stat().st_mtime)
        if result_file_type.is_correct_report_type(str(newest_res_file.name)):
            revisions.append((commit_hash,
                              result_file_type.get_status_from_result_file(
                                  str(newest_res_file))))

    return revisions
