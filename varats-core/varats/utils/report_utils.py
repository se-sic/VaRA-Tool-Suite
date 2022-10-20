"""Additional report utilities for moving and renaming report files."""
import varats.report.report as r


# TODO: find a good name
def adapted_report_filename_status(
    current: r.ReportFilename, new_status: r.FileStatusExtension
) -> r.ReportFilename:
    """Returns a new report filename, adapted with the new file extension
    `new_status`."""
    desired_filename = r.ReportFilename.get_file_name(
        current.experiment_shorthand, current.report_shorthand,
        current.project_name, current.binary_name, current.commit_hash,
        current.uuid, new_status, current.file_suffix, current.config_id
    )

    return desired_filename


def adapted_report_filepath_status(
    current: r.ReportFilepath, new_status: r.FileStatusExtension
) -> r.ReportFilepath:
    return r.ReportFilepath(
        current.base_path,
        adapted_report_filename_status(current.report_filename, new_status)
    )
