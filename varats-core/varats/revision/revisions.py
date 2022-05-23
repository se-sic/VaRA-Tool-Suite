"""
Module for handling revision specific files.

When analyzing a project, result files are generated for specific project
revisions.  This module provides functionality to manage and access these
revision specific files, e.g., to get all files of a specific report that have
been processed successfully.
"""

import typing as tp
from collections import defaultdict
from pathlib import Path

from benchbuild.project import Project

from varats.project.project_util import (
    get_project_cls_by_name,
    get_primary_project_source,
)
from varats.report.report import FileStatusExtension, BaseReport, ReportFilename
from varats.utils.git_util import ShortCommitHash, CommitHashTy, CommitHash
from varats.utils.settings import vara_cfg


def is_revision_blocked(
    revision: CommitHash, project_cls: tp.Type[Project]
) -> bool:
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
        return tp.cast(bool, source.is_blocked_revision(revision.hash)[0])
    return False


def filter_blocked_revisions(
    revisions: tp.List[CommitHashTy], project_cls: tp.Type[Project]
) -> tp.List[CommitHashTy]:
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
    project_name: str, result_file_type: tp.Type[BaseReport]
) -> tp.Dict[ShortCommitHash, tp.List[Path]]:
    """
    Returns a dict that maps the commit_hash to a list of all result files, of
    type result_file_type, for that commit.

    Args:
        project_name: target project
        result_file_type: the type of the result file
    """
    res_dir = Path(f"{vara_cfg()['result_dir']}/{project_name}/")

    result_files: tp.DefaultDict[ShortCommitHash, tp.List[Path]] = defaultdict(
        list
    )  # maps commit hash -> list of res files (success or fail)
    if not res_dir.exists():
        return result_files

    for res_file in res_dir.iterdir():
        report_file = ReportFilename(res_file)
        if report_file.is_result_file(
        ) and result_file_type.is_correct_report_type(res_file.name):
            commit_hash = report_file.commit_hash
            result_files[commit_hash].append(res_file)

    return result_files


def __get_files_with_status(
    project_name: str,
    result_file_type: tp.Type[BaseReport],
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
            if ReportFilename(result_file.name).file_status in file_statuses:
                processed_revisions_paths.append(result_file)

    return processed_revisions_paths


def get_all_revisions_files(
    project_name: str,
    result_file_type: tp.Type[BaseReport],
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
    result_file_type: tp.Type[BaseReport],
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
        project_name, result_file_type, [FileStatusExtension.SUCCESS],
        file_name_filter, only_newest
    )


def get_failed_revisions_files(
    project_name: str,
    result_file_type: tp.Type[BaseReport],
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
        [FileStatusExtension.FAILED, FileStatusExtension.COMPILE_ERROR],
        file_name_filter, only_newest
    )


def get_processed_revisions(
    project_name: str, result_file_type: tp.Type[BaseReport]
) -> tp.List[ShortCommitHash]:
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
        ReportFilename(x.name).commit_hash
        for x in get_processed_revisions_files(project_name, result_file_type)
    ]


def get_failed_revisions(
    project_name: str, result_file_type: tp.Type[BaseReport]
) -> tp.List[ShortCommitHash]:
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
        if ReportFilename(newest_res_file.name).has_status_failed():
            failed_revisions.append(commit_hash)

    return failed_revisions


def __get_tag_for_revision(
    revision: ShortCommitHash,
    file_list: tp.List[Path],
    project_cls: tp.Type[Project],
    result_file_type: tp.Type[BaseReport],
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
        return FileStatusExtension.BLOCKED

    newest_res_file = max(file_list, key=lambda x: x.stat().st_mtime)
    if result_file_type.is_correct_report_type(newest_res_file.name):
        return ReportFilename(str(newest_res_file)).file_status

    return FileStatusExtension.MISSING


def get_tagged_revisions(
    project_cls: tp.Type[Project],
    result_file_type: tp.Type[BaseReport],
    tag_blocked: bool = True,
    revision_filter: tp.Optional[tp.Callable[[Path], bool]] = None
) -> tp.List[tp.Tuple[ShortCommitHash, FileStatusExtension]]:
    """
    Calculates a list of revisions of a project tagged with the file status. If
    two files exists the newest is considered for detecting the status.

    Args:
        project_cls: target project
        result_file_type: the type of the result file
        tag_blocked: whether to tag blocked revisions as blocked
        revision_filter: to select a specific subset of revisions

    Returns:
        list of tuples (revision, ``FileStatusExtension``)
    """
    revisions = []
    result_files = __get_result_files_dict(project_cls.NAME, result_file_type)
    for commit_hash, file_list in result_files.items():
        filtered_file_list = list(
            filter(revision_filter, file_list)
        ) if revision_filter else file_list

        if filtered_file_list:
            tag = __get_tag_for_revision(
                commit_hash, filtered_file_list, project_cls, result_file_type,
                tag_blocked
            )
        else:
            tag = FileStatusExtension.MISSING

        revisions.append((commit_hash, tag))

    return revisions


def get_tagged_revision(
    revision: ShortCommitHash, project_name: str,
    result_file_type: tp.Type[BaseReport]
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
        return FileStatusExtension.MISSING
    return __get_tag_for_revision(
        revision, result_files[revision], project_cls, result_file_type
    )
