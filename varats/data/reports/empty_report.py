"""
Empty report implementation for testing.
"""

from varats.data.report import BaseReport, FileStatusExtension


class EmptyReport(BaseReport):
    """
    An empty report for testing.
    Nothing gets printed into the report and the result file has no file type.
    """

    SHORTHAND = "EMPTY"

    @staticmethod
    def get_file_name(project_name: str, binary_name: str,
                      project_version: str, project_uuid: str,
                      extension_type: FileStatusExtension,
                      file_ext=".txt") -> str:
        """
        Generates a filename for a commit report without any file ending.
        """
        return BaseReport.get_file_name(EmptyReport.SHORTHAND, project_name,
                                        binary_name, project_version,
                                        project_uuid, extension_type,
                                        file_ext)
