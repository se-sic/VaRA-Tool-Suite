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
from varats.report.report import (
    FileStatusExtension,
    BaseReport,
    ReportFilename,
    ReportFilepath,
)
from varats.utils.git_util import ShortCommitHash, CommitHashTy, CommitHash
from varats.utils.settings import vara_cfg

if tp.TYPE_CHECKING:
    import varats.experiment.experiment_util as exp_u


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
    project_name: str,
    experiment_type: tp.Type["exp_u.VersionExperiment"],
    report_type: tp.Optional[tp.Type[BaseReport]] = None
) -> tp.Dict[ShortCommitHash, tp.List[ReportFilepath]]:
    """
    Returns a dict that maps the commit_hash to a list of all result files of
    the given type for that commit.

    Args:
        project_name: target project
        experiment_type: the experiment type that created the result files
        report_type: the report type of the result files;
                     defaults to experiment's main report
    """
    res_dir = Path(f"{vara_cfg()['result_dir']}/{project_name}/")

    # maps commit hash -> list of res files (success or fail)
    result_files: tp.DefaultDict[ShortCommitHash,
                                 tp.List[ReportFilepath]] = defaultdict(list)
    if not res_dir.exists():
        return result_files

    if report_type is None:
        report_type = experiment_type.report_spec().main_report

    for res_file in res_dir.rglob("*"):
        if res_file.is_dir():
            continue

        report_filepath = ReportFilepath.construct(res_file, res_dir)
        report_file = report_filepath.report_filename
        if report_file.is_result_file(
        ) and report_file.report_shorthand == report_type.shorthand(
        ) and report_file.experiment_shorthand == experiment_type.shorthand():
            commit_hash = report_file.commit_hash
            result_files[commit_hash].append(report_filepath)

    return result_files


def __get_files_with_status(
    project_name: str,
    file_statuses: tp.List[FileStatusExtension],
    experiment_type: tp.Type["exp_u.VersionExperiment"],
    report_type: tp.Optional[tp.Type[BaseReport]] = None,
    file_name_filter: tp.Callable[[str], bool] = lambda x: False,
    only_newest: bool = True
) -> tp.List[ReportFilepath]:
    """
    Find all file paths to result files with given file statuses.

    Args:
        project_name: target project
        file_statuses: a list of statuses the files should have
        experiment_type: the experiment type that created the result files
        report_type: the report type of the result files;
                     defaults to experiment's main report
        file_name_filter: optional filter to exclude certain files; returns
                          true if the file_name should not be checked
        only_newest: whether to include all result files, or only the newest;
                     if ``False``, result files for the same revision are sorted
                     descending by the file's mtime

    Returns:
        a list of file paths to matching revision files
    """
    processed_revisions_paths = []

    result_files = __get_result_files_dict(
        project_name, experiment_type, report_type
    )
    for value in result_files.values():
        sorted_res_files = sorted(
            value, key=lambda x: x.full_path().stat().st_mtime, reverse=True
        )
        if only_newest:
            sorted_res_files = [sorted_res_files[0]]
        for result_file in sorted_res_files:
            if file_name_filter(result_file.report_filename.filename):
                continue
            if result_file.report_filename.file_status in file_statuses:
                processed_revisions_paths.append(result_file)

    return processed_revisions_paths


def get_all_revisions_files(
    project_name: str,
    experiment_type: tp.Type["exp_u.VersionExperiment"],
    report_type: tp.Optional[tp.Type[BaseReport]] = None,
    file_name_filter: tp.Callable[[str], bool] = lambda x: False,
    only_newest: bool = True
) -> tp.List[ReportFilepath]:
    """
    Find all file paths to revision files.

    Args:
        project_name: target project
        file_name_filter: optional filter to exclude certain files; returns
                          true if the file_name should not be checked
        experiment_type: the experiment type that created the result files
        report_type: the report type of the result files;
                     defaults to experiment's main report
        only_newest: whether to include all result files, or only the newest;
                     if ``False``, result files for the same revision are sorted
                     descending by the file's mtime

    Returns:
        a list of file paths to correctly processed revision files
    """
    return __get_files_with_status(
        project_name, list(FileStatusExtension.get_physical_file_statuses()),
        experiment_type, report_type, file_name_filter, only_newest
    )


def get_processed_revisions_files(
    project_name: str,
    experiment_type: tp.Type["exp_u.VersionExperiment"],
    report_type: tp.Optional[tp.Type[BaseReport]] = None,
    file_name_filter: tp.Callable[[str], bool] = lambda x: False,
    only_newest: bool = True
) -> tp.List[ReportFilepath]:
    """
    Find all file paths to correctly processed revision files.

    Args:
        project_name: target project
        file_name_filter: optional filter to exclude certain files; returns
                          true if the file_name should not be checked
        experiment_type: the experiment type that created the result files
        report_type: the report type of the result files;
                     defaults to experiment's main report
        only_newest: whether to include all result files, or only the newest;
                     if ``False``, result files for the same revision are sorted
                     descending by the file's mtime

    Returns:
        a list of file paths to correctly processed revision files
    """
    return __get_files_with_status(
        project_name, [FileStatusExtension.SUCCESS], experiment_type,
        report_type, file_name_filter, only_newest
    )


def get_failed_revisions_files(
    project_name: str,
    experiment_type: tp.Type["exp_u.VersionExperiment"],
    report_type: tp.Optional[tp.Type[BaseReport]] = None,
    file_name_filter: tp.Callable[[str], bool] = lambda x: False,
    only_newest: bool = True
) -> tp.List[ReportFilepath]:
    """
    Find all file paths to failed revision files.

    Args:
        project_name: target project
        file_name_filter: optional filter to exclude certain files; returns
                          ``True`` if the file_name should not be included
        experiment_type: the experiment type that created the result files
        report_type: the report type of the result files;
                     defaults to experiment's main report
        only_newest: whether to include all result files, or only the newest;
                     if ``False``, result files for the same revision are sorted
                     descending by the file's mtime

    Returns:
        a list of file paths to failed revision files
    """
    return __get_files_with_status(
        project_name,
        [FileStatusExtension.FAILED, FileStatusExtension.COMPILE_ERROR],
        experiment_type, report_type, file_name_filter, only_newest
    )


def get_processed_revisions(
    project_name: str,
    experiment_type: tp.Type["exp_u.VersionExperiment"],
    report_type: tp.Optional[tp.Type[BaseReport]] = None,
) -> tp.List[ShortCommitHash]:
    """
    Calculates a list of revisions of a project that have already been processed
    successfully.

    Args:
        project_name: target project
        experiment_type: the experiment type that created the result files
        report_type: the report type of the result files;
                     defaults to experiment's main report

    Returns:
        list of correctly process revisions
    """
    return [
        x.report_filename.commit_hash for x in get_processed_revisions_files(
            project_name, experiment_type, report_type
        )
    ]


def get_failed_revisions(
    project_name: str,
    experiment_type: tp.Type["exp_u.VersionExperiment"],
    report_type: tp.Optional[tp.Type[BaseReport]] = None,
) -> tp.List[ShortCommitHash]:
    """
    Calculates a list of revisions of a project that have failed.

    Args:
        project_name: target project
        experiment_type: the experiment type that created the result files
        report_type: the report type of the result files;
                     defaults to experiment's main report

    Returns:
        list of failed revisions
    """
    failed_revisions = []

    result_files = __get_result_files_dict(
        project_name, experiment_type, report_type
    )
    for commit_hash, value in result_files.items():
        newest_res_file = max(
            value, key=lambda x: x.full_path().stat().st_mtime
        )
        if newest_res_file.report_filename.has_status_failed():
            failed_revisions.append(commit_hash)

    return failed_revisions


def __get_tag_for_revision(
    revision: ShortCommitHash,
    file_list: tp.List[ReportFilepath],
    project_cls: tp.Type[Project],
    experiment_type: tp.Type["exp_u.VersionExperiment"],
    report_type: tp.Optional[tp.Type[BaseReport]] = None,
    tag_blocked: bool = True
) -> FileStatusExtension:
    """
    Calculates the file status for a revision.

    Args:
        revision: the revision to get the status for
        file_list: the list of result files for the revision
        project_cls: the project class the revision belongs to
        experiment_type: the experiment type that created the result files
        report_type: the report type of the result files;
                     defaults to experiment's main report

    Returns:
        the status for the revision
    """
    if tag_blocked and is_revision_blocked(revision, project_cls):
        return FileStatusExtension.BLOCKED

    if report_type is None:
        report_type = experiment_type.report_spec().main_report

    newest_res_file = max(
        file_list, key=lambda x: x.full_path().stat().st_mtime
    )
    report_file = newest_res_file.report_filename
    if report_file.is_result_file(
    ) and report_file.report_shorthand == report_type.shorthand(
    ) and report_file.experiment_shorthand == experiment_type.shorthand():
        return report_file.file_status

    return FileStatusExtension.MISSING


def _split_into_config_file_lists(
    report_files: tp.List[ReportFilepath]
) -> tp.Dict[tp.Optional[int], tp.List[ReportFilepath]]:
    config_id_mapping: tp.DefaultDict[
        tp.Optional[int], tp.List[ReportFilepath]] = defaultdict(list)

    for report_file in report_files:
        config_id_mapping[report_file.report_filename.config_id
                         ].append(report_file)

    return config_id_mapping


def get_tagged_revisions(
    project_cls: tp.Type[Project],
    experiment_type: tp.Type["exp_u.VersionExperiment"],
    report_type: tp.Optional[tp.Type[BaseReport]] = None,
    tag_blocked: bool = True,
    revision_filter: tp.Optional[tp.Callable[[ReportFilepath], bool]] = None
) -> tp.Dict[ShortCommitHash, tp.Dict[tp.Optional[int], FileStatusExtension]]:
    """
    Calculates a list of revisions of a project tagged with the file status. If
    two files exists the newest is considered for detecting the status.

    Args:
        project_cls: target project
        experiment_type: the experiment type that created the result files
        report_type: the report type of the result files;
                     defaults to experiment's main report
        tag_blocked: whether to tag blocked revisions as blocked
        revision_filter: to select a specific subset of revisions

    Returns:
        list of tuples (revision, ``FileStatusExtension``)
    """
    revisions: tp.DefaultDict[ShortCommitHash,
                              tp.Dict[tp.Optional[int],
                                      FileStatusExtension]] = defaultdict(dict)
    result_files = __get_result_files_dict(
        project_cls.NAME, experiment_type, report_type
    )

    for commit_hash, file_list in result_files.items():
        filtered_file_list = list(
            filter(revision_filter, file_list)
        ) if revision_filter else file_list

        # Split file list into config id sets
        for config_id, config_specific_file_list \
                in _split_into_config_file_lists(filtered_file_list).items():
            tag = __get_tag_for_revision(
                commit_hash, config_specific_file_list, project_cls,
                experiment_type, report_type, tag_blocked
            )

            revisions[commit_hash][config_id] = tag

    return revisions


def get_tagged_revision(
    revision: ShortCommitHash,
    project_name: str,
    experiment_type: tp.Type["exp_u.VersionExperiment"],
    report_type: tp.Optional[tp.Type[BaseReport]] = None
) -> FileStatusExtension:
    """
    Calculates the file status for a revision. If two files exists the newest is
    considered for detecting the status.

    Args:
        revision: the revision to get the status for
        project_name: target project
        experiment_type: the experiment type that created the result files
        report_type: the report type of the result files;
                     defaults to experiment's main report

    Returns:
        the status for the revision
    """
    project_cls = get_project_cls_by_name(project_name)
    result_files = __get_result_files_dict(
        project_name, experiment_type, report_type
    )

    if revision not in result_files.keys():
        return FileStatusExtension.MISSING
    return __get_tag_for_revision(
        revision, result_files[revision], project_cls, experiment_type,
        report_type
    )
