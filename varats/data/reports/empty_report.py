"""
Empty report implementation for testing.
"""

from varats.data.report import BaseReport, FileStatusExtension


class EmptyReport(BaseReport):

    SHORTHAND = "EMPTY"

    @staticmethod
    def get_file_name(project_name: str, binary_name: str,
                      project_version: str, project_uuid: str,
                      extension_type: FileStatusExtension) -> str:
        """
        Generates a filename for a commit report
        """
        return BaseReport.get_file_name(EmptyReport.SHORTHAND, project_name,
                                        binary_name, project_version,
                                        project_uuid, extension_type)
