"""
Report that simply takes the output of an phasar analysis.
"""

from varats.data.report import BaseReport, FileStatusExtension


class PhasarReport(BaseReport):
    """
    The phasar report produces json files with the output for each file.
    """

    SHORTHAND = "PHASAR"
    FILETYPE = "json"

    @staticmethod
    def get_file_name(project_name: str, binary_name: str,
                      project_version: str, project_uuid: str,
                      extension_type: FileStatusExtension,
                      file_ext: str = ".json") -> str:
        """
        Generates a filename for a dataflow analysis with json file type.
        """
        return BaseReport.get_file_name(PhasarReport.SHORTHAND, project_name,
                                        binary_name, project_version,
                                        project_uuid, extension_type,
                                        file_ext)
