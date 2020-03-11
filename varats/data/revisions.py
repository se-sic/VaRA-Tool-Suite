"""
Module for handling the state of project revisions in VaRA.
"""

import typing as tp
from collections import defaultdict
from pathlib import Path

from benchbuild.project import Project

from varats.utils.project_util import get_project_cls_by_name
from varats.settings import CFG
from varats.data.report import MetaReport, FileStatusExtension


def __get_result_files_dict(
        project_name: str,
        result_file_type: MetaReport) -> tp.Dict[str, tp.List[Path]]:
    """
    Returns a dict that maps the commit_hash to a list of all result files, of
    type result_file_type, for that commit.

    Args:
        project_name: target project
        result_file_type: the type of the result file
    """
    res_dir = Path("{result_folder}/{project_name}/".format(
        result_folder=CFG["result_dir"], project_name=project_name))

    result_files: tp.DefaultDict[str, tp.List[Path]] = defaultdict(
        list)  # maps commit hash -> list of res files (success or fail)
    if not res_dir.exists():
        return result_files

    for res_file in res_dir.iterdir():
        if result_file_type.is_result_file(
                res_file.name) and result_file_type.is_correct_report_type(
                    res_file.name):
            commit_hash = result_file_type.get_commit_hash_from_result_file(
                res_file.name)
            result_files[commit_hash].append(res_file)

    return result_files


def __get_supplementary_result_files_dict(
    project_name: str,
    result_file_type: MetaReport,
    revision: tp.Optional[str] = None,
) -> tp.Dict[tp.Tuple[str, str], tp.List[Path]]:
    """
    Returns a dict that maps the commit_hash and the info_type to a list
    of all supplementary result files for that commit and info_type.
    If an (optional) revision is specified the nonly result files for that
    commit are returned.

    Args:
        project_name: target project
        result_file_type: the type of the result file
        revision (str): The revision for which the result files should
                        be returned.

    Returns:
        Dict that maps (commit_hash, info_type) to list of result files
    """
    res_dir = Path("{result_folder}/{project_name}/".format(
        result_folder=CFG["result_dir"], project_name=project_name))

    result_files: tp.DefaultDict[tp.Tuple[
        str, str], tp.List[Path]] = defaultdict(
            list)  # maps (commit_hash, suppl._file_type) -> list of res files

    if res_dir.exists():
        for res_file in res_dir.iterdir():
            if result_file_type.is_result_file_supplementary(res_file.name):
                commit_hash = result_file_type.\
                    get_commit_hash_from_supplementary_result_file(
                        res_file.name)
                info_type = result_file_type.\
                    get_info_type_from_supplementary_result_file(
                        res_file.name)
                if revision is None or commit_hash == revision:
                    result_files[(commit_hash, info_type)].append(res_file)

    return result_files


def get_processed_revisions_files(
    project_name: str,
    result_file_type: MetaReport,
    file_name_filter: tp.Optional[tp.Callable[[str], bool]] = None
) -> tp.List[Path]:
    """
    Returns a list of file paths to correctly processed revision files.

    Args:
        project_name: target project
        result_file_type: the type of the result file
        file_name_filter: optional filter to exclude certain files,
                            returns true; if the file_name should not be
                            checked
    """
    processed_revisions_paths = []

    result_files = __get_result_files_dict(project_name, result_file_type)
    for value in result_files.values():
        newest_res_file = max(value, key=lambda x: Path(x).stat().st_mtime)
        if file_name_filter is not None:
            if file_name_filter(newest_res_file.name):
                continue
        if result_file_type.result_file_has_status_success(
                newest_res_file.name):
            processed_revisions_paths.append(newest_res_file)

    return processed_revisions_paths


def get_processed_revisions(project_name: str,
                            result_file_type: MetaReport) -> tp.List[str]:
    """
    Calculates a list of revisions of a project that have already
    been processed successfully.

    Args:
        project_name: target project
        result_file_type: the type of the result file
    """
    return [
        result_file_type.get_commit_hash_from_result_file(x.name)
        for x in get_processed_revisions_files(project_name, result_file_type)
    ]


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
        if result_file_type.result_file_has_status_failed(newest_res_file.name):
            failed_revisions.append(commit_hash)

    return failed_revisions


def __get_tag_for_revision(revision: str,
                           file_list: tp.List[Path],
                           project_cls: Project,
                           result_file_type: MetaReport,
                           tag_blocked: bool = True) -> FileStatusExtension:
    """
    Calculates the file status for a revision.

    Args:
        revision: the revision to get the status for
        file_list: the list of result files for the revision
        project_cls: the project class the revision belongs to
        result_file_type: the report type to be considered

    Returns:
        the status for the revision
    """
    if tag_blocked and hasattr(
            project_cls, "is_blocked_revision"
    ) and project_cls.is_blocked_revision(revision)[0]:
        return FileStatusExtension.Blocked
    else:
        newest_res_file = max(file_list, key=lambda x: x.stat().st_mtime)
        if result_file_type.is_correct_report_type(str(newest_res_file.name)):
            return result_file_type.get_status_from_result_file(
                str(newest_res_file))
        else:
            return FileStatusExtension.Missing


def get_tagged_revisions(
    project_name: str,
    result_file_type: MetaReport,
    tag_blocked: bool = True
) -> tp.List[tp.Tuple[str, FileStatusExtension]]:
    """
    Calculates a list of revisions of a project tagged with the file status.
    If two files exists the newest is considered for detecting the status.

    Args:
        project_name: target project
        result_file_type: the type of the result file
        tag_blocked: whether to tag blocked revisions as blocked
    """
    revisions = []

    project_cls = get_project_cls_by_name(project_name)
    result_files = __get_result_files_dict(project_name, result_file_type)
    for commit_hash, file_list in result_files.items():
        revisions.append(
            (commit_hash,
             __get_tag_for_revision(commit_hash, file_list, project_cls,
                                    result_file_type, tag_blocked)))

    return revisions


def get_tagged_revision(revision: str, project_name: str,
                        result_file_type: MetaReport) -> FileStatusExtension:
    """
    Calculates the file status for a revision.
    If two files exists the newest is considered for detecting the status.

    Args:
        revision: the revision to get the status for
        project_name: target project
        result_file_type: the type of the result file

    Returns:
        the status for the revision
    """
    project_cls = get_project_cls_by_name(project_name)
    result_files = __get_result_files_dict(project_name, result_file_type)

    if revision not in result_files.keys():
        return FileStatusExtension.Missing
    return __get_tag_for_revision(revision, result_files[revision], project_cls,
                                  result_file_type)


def get_supplementary_result_files(
    project_name: str,
    result_file_type: MetaReport,
    revision: tp.Optional[str] = None,
    suppl_info_type: tp.Optional[str] = None
) -> tp.List[tp.Tuple[Path, str, str]]:
    """
    Returns the current supplementary result files for a given project and
    report type.
    If a specific revision is specified then only the result files for the
    passed revision are returned, otherwise all files for all available
    revisions are returned.

    Args:
        project_name (str): target project
        result_file_type (MetaReport): the type of the result file
        revision (str): The revision for which the result files should
                        be returned.
        suppl_info_type (str): Only include result files of the specified type

    Returns:
        [(Path, str, str)]: List of tuples of result file path, revision,
                            and supplementary result file type
    """
    result_files = __get_supplementary_result_files_dict(
        project_name, result_file_type, revision)

    result = []

    for (commit_hash, info_type), file_list in result_files.items():
        if (suppl_info_type is None) or (info_type == suppl_info_type):
            newest_res_file = max(file_list, key=lambda x: x.stat().st_mtime)
            result.append((newest_res_file, commit_hash, info_type))

    return result
