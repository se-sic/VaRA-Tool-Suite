"""
Module for all reports generated for taint flow analyses."
"""

from varats.data.report import BaseReport, FileStatusExtension


class TaintReport(BaseReport):
    """
    Print the result of filechecking multiple ll files in a readable manner.
    """

    SHORTHAND = "TAINT"

    @staticmethod
    def get_file_name(project_name: str, binary_name: str,
                      project_version: str, project_uuid: str,
                      extension_type: FileStatusExtension) -> str:
        """
        Generates a filename for a commit report
        """
        return BaseReport.get_file_name(TaintReport.SHORTHAND, project_name,
                                        binary_name, project_version,
                                        project_uuid, extension_type)
