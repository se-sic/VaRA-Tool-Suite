"""
Module for handling revision specific files.

When analyzing a project, result files are generated for specific project
revisions.  This module provides functionality to manage and access these
revision specific files, e.g., to get all files of a specific report that have
been process successfully.
"""

import typing as tp
from collections import defaultdict
from pathlib import Path

from benchbuild.project import Project

from varats.data.report import FileStatusExtension, MetaReport
from varats.utils.project_util import (
    get_project_cls_by_name,
    get_primary_project_source,
)
from varats.utils.settings import vara_cfg


def is_revision_blocked(revision: str, project_cls: tp.Type[Project]) -> bool:
    """
    Checks if a revision is blocked on a given project.

    Args:
        revision: the revision
        project_cls: the project class the revision belongs to

    Returns:
        filtered revision list
    """
    source = get_primary_project_source(project_cls.NAME)
    if hasattr(source, "is_blocked_revision"):
        return tp.cast(bool, source.is_blocked_revision(revision)[0])
    return False


def filter_blocked_revisions(
    revisions: tp.List[str], project_cls: tp.Type[Project]
) -> tp.List[str]:
    """
    Filter out all blocked revisions.

    Args:
        revisions: list of revisions
        project_cls: the project class the revisions belong to

    Returns:
        filtered revision list
    """
    return [
        rev for rev in revisions if not is_revision_blocked(rev, project_cls)
    ]


def __get_result_files_dict(
    project_name: str, result_file_type: MetaReport
) -> tp.Dict[str, tp.List[Path]]:
    """
    Returns a dict that maps the commit_hash to a list of all result files, of
    type result_file_type, for that commit.

    Args:
        project_name: target project
        result_file_type: the type of the result file
    """
    res_dir = Path(f"{vara_cfg()['result_dir']}/{project_name}/")

    result_files: tp.DefaultDict[str, tp.List[Path]] = defaultdict(
        list
    )  # maps commit hash -> list of res files (success or fail)
    if not res_dir.exists():
        return result_files

    for res_file in res_dir.iterdir():
        if result_file_type.is_result_file(
            res_file.name
        ) and result_file_type.is_correct_report_type(res_file.name):
            commit_hash = result_file_type.get_commit_hash_from_result_file(
                res_file.name
            )
            result_files[commit_hash].append(res_file)

    return result_files


def __get_supplementary_result_files_dict(
    project_name: str,
    result_file_type: MetaReport,
    revision: tp.Optional[str] = None,
) -> tp.Dict[tp.Tuple[str, str], tp.List[Path]]:
    """
    Returns a dict that maps the commit_hash and the info_type to a list of all
    supplementary result files for that commit and info_type. If an (optional)
    revision is specified the nonly result files for that commit are returned.

    Args:
        project_name: target project
        result_file_type: the type of the result file
        revision (str): The revision for which the result files should
                        be returned.

    Returns:
        Dict that maps (commit_hash, info_type) to list of result files
    """
    res_dir = Path(f"{vara_cfg()['result_dir']}/{project_name}/")

    result_files: tp.DefaultDict[tp.Tuple[
        str, str], tp.List[Path]] = defaultdict(
            list
        )  # maps (commit_hash, suppl._file_type) -> list of res files

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


def __get_files_with_status(
    project_name: str,
    result_file_type: MetaReport,
    file_statuses: tp.List[FileStatusExtension],
    file_name_filter: tp.Callable[[str], bool] = lambda x: False,
    only_newest: bool = True
) -> tp.List[Path]:
    """
    Find all file paths to revision files with given file statuses.

    Args:
        project_name: target project
        result_file_type: the type of the result file
        file_statuses: a list of statuses the files should have
        file_name_filter: optional filter to exclude certain files; returns
                          true if the file_name should not be checked
        only_newest: whether to include all result files, or only the newest;
                     if ``False``, result files for the same revision are sorted
                     descending by the file's mtime

    Returns:
        a list of file paths to matching revision files
    """
    processed_revisions_paths = []

    result_files = __get_result_files_dict(project_name, result_file_type)
    for value in result_files.values():
        sorted_res_files = sorted(
            value, key=lambda x: Path(x).stat().st_mtime, reverse=True
        )
        if only_newest:
            sorted_res_files = [sorted_res_files[0]]
        for result_file in sorted_res_files:
            if file_name_filter(result_file.name):
                continue
            if result_file_type.get_status_from_result_file(
                result_file.name
            ) in file_statuses:
                processed_revisions_paths.append(result_file)

    return processed_revisions_paths


def get_all_revisions_files(
    project_name: str,
    result_file_type: MetaReport,
    file_name_filter: tp.Callable[[str], bool] = lambda x: False,
    only_newest: bool = True
) -> tp.List[Path]:
    """
    Find all file paths to revision files.

    Args:
        project_name: target project
        result_file_type: the type of the result file
        file_name_filter: optional filter to exclude certain files; returns
                          true if the file_name should not be checked
        only_newest: whether to include all result files, or only the newest;
                     if ``False``, result files for the same revision are sorted
                     descending by the file's mtime

    Returns:
        a list of file paths to correctly processed revision files
    """
    return __get_files_with_status(
        project_name, result_file_type,
        list(FileStatusExtension.get_physical_file_statuses()),
        file_name_filter, only_newest
    )


def get_processed_revisions_files(
    project_name: str,
    result_file_type: MetaReport,
    file_name_filter: tp.Callable[[str], bool] = lambda x: False,
    only_newest: bool = True
) -> tp.List[Path]:
    """
    Find all file paths to correctly processed revision files.

    Args:
        project_name: target project
        result_file_type: the type of the result file
        file_name_filter: optional filter to exclude certain files; returns
                          true if the file_name should not be checked
        only_newest: whether to include all result files, or only the newest;
                     if ``False``, result files for the same revision are sorted
                     descending by the file's mtime

    Returns:
        a list of file paths to correctly processed revision files
    """
    return __get_files_with_status(
        project_name, result_file_type, [FileStatusExtension.Success],
        file_name_filter, only_newest
    )


def get_failed_revisions_files(
    project_name: str,
    result_file_type: MetaReport,
    file_name_filter: tp.Callable[[str], bool] = lambda x: False,
    only_newest: bool = True
) -> tp.List[Path]:
    """
    Find all file paths to failed revision files.

    Args:
        project_name: target project
        result_file_type: the type of the result file
        file_name_filter: optional filter to exclude certain files; returns
                          ``True`` if the file_name should not be included
        only_newest: whether to include all result files, or only the newest;
                     if ``False``, result files for the same revision are sorted
                     descending by the file's mtime

    Returns:
        a list of file paths to failed revision files
    """
    return __get_files_with_status(
        project_name, result_file_type,
        [FileStatusExtension.Failed, FileStatusExtension.CompileError],
        file_name_filter, only_newest
    )


def get_processed_revisions(project_name: str,
                            result_file_type: MetaReport) -> tp.List[str]:
    """
    Calculates a list of revisions of a project that have already been processed
    successfully.

    Args:
        project_name: target project
        result_file_type: the type of the result file

    Returns:
        list of correctly process revisions
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

    Returns:
        list of failed revisions
    """
    failed_revisions = []

    result_files = __get_result_files_dict(project_name, result_file_type)
    for commit_hash, value in result_files.items():
        newest_res_file = max(value, key=lambda x: Path(x).stat().st_mtime)
        if result_file_type.result_file_has_status_failed(newest_res_file.name):
            failed_revisions.append(commit_hash)

    return failed_revisions


def __get_tag_for_revision(
    revision: str,
    file_list: tp.List[Path],
    project_cls: tp.Type[Project],
    result_file_type: MetaReport,
    tag_blocked: bool = True
) -> FileStatusExtension:
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
    if tag_blocked and is_revision_blocked(revision, project_cls):
        return FileStatusExtension.Blocked

    newest_res_file = max(file_list, key=lambda x: x.stat().st_mtime)
    if result_file_type.is_correct_report_type(str(newest_res_file.name)):
        return result_file_type.get_status_from_result_file(
            str(newest_res_file)
        )

    return FileStatusExtension.Missing


def get_tagged_revisions(
    project_cls: tp.Type[Project],
    result_file_type: MetaReport,
    tag_blocked: bool = True
) -> tp.List[tp.Tuple[str, FileStatusExtension]]:
    """
    Calculates a list of revisions of a project tagged with the file status. If
    two files exists the newest is considered for detecting the status.

    Args:
        project_cls: target project
        result_file_type: the type of the result file
        tag_blocked: whether to tag blocked revisions as blocked

    Returns:
        list of tuples (revision, ``FileStatusExtension``)
    """
    revisions = []
    result_files = __get_result_files_dict(project_cls.NAME, result_file_type)
    for commit_hash, file_list in result_files.items():
        revisions.append((
            commit_hash,
            __get_tag_for_revision(
                commit_hash, file_list, project_cls, result_file_type,
                tag_blocked
            )
        ))

    return revisions


def get_tagged_revision(
    revision: str, project_name: str, result_file_type: MetaReport
) -> FileStatusExtension:
    """
    Calculates the file status for a revision. If two files exists the newest is
    considered for detecting the status.

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
    return __get_tag_for_revision(
        revision, result_files[revision], project_cls, result_file_type
    )


def get_supplementary_result_files(
    project_name: str,
    result_file_type: MetaReport,
    revision: tp.Optional[str] = None,
    suppl_info_type: tp.Optional[str] = None
) -> tp.List[tp.Tuple[Path, str, str]]:
    """
    Returns the current supplementary result files for a given project and
    report type. If a specific revision is specified then only the result files
    for the passed revision are returned, otherwise all files for all available
    revisions are returned.

    Args:
        project_name: target project
        result_file_type: the type of the result file
        revision: the revision for which the result files should
                        be returned
        suppl_info_type: only include result files of the specified type

    Returns:
        list of tuples of result file path, revision, and supplementary result
        file type
    """
    result_files = __get_supplementary_result_files_dict(
        project_name, result_file_type, revision
    )

    result = []

    for (commit_hash, info_type), file_list in result_files.items():
        if (suppl_info_type is None) or (info_type == suppl_info_type):
            newest_res_file = max(file_list, key=lambda x: x.stat().st_mtime)
            result.append((newest_res_file, commit_hash, info_type))

    return result
