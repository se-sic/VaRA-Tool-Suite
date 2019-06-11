"""
Module for handling the state of project revisions in VaRA.
"""

from pathlib import Path

from varats.settings import CFG


def get_proccessed_revisions(project_name: str, result_file_type) -> [str]:
    """
    Calculates a list of revisions of a project that have already
    been processed.

    Args:
        project_name: target project
        result_file_type: the type of the result file
    """
    res_dir = Path("{result_folder}/{project_name}/".format(
        result_folder=CFG["result_dir"], project_name=project_name))

    processed_revision = []
    if res_dir.exists():
        for res_file in res_dir.iterdir():
            if not str(res_file.stem).startswith("{}-".format(project_name)):
                continue
            match = result_file_type.FILE_NAME_REGEX.search(res_file.stem)
            if match:
                processed_revision.append(match.group("file_commit_hash"))

    return processed_revision
