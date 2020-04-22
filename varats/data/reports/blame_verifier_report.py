from varats.data.report import BaseReport, MetaReport, FileStatusExtension


class BlameVerifierReport(BaseReport):
    """
    TODO: Add further description (Currently empty report)
    Full BlameVerifier report.
    """

    SHORTHAND = "BVR"

    @staticmethod
    def get_file_name(project_name: str,
                      binary_name: str,
                      project_version: str,
                      project_uuid: str,
                      extension_type: FileStatusExtension,
                      file_ext: str = ".txt") -> str:
        """
        Generates a filename for a commit report without any file ending.

        Args:
            project_name: name of the project for which the report was generated
            binary_name: name of the binary for which the report was generated
            project_version: version of the analyzed project, i.e., commit hash
            project_uuid: benchbuild uuid for the experiment run
            extension_type: to specify the status of the generated report
            file_ext: file extension of the report file

        Returns:
            name for the report file that can later be uniquely identified
        """
        return MetaReport.get_file_name(BlameVerifierReport.SHORTHAND, project_name,
                                        binary_name, project_version,
                                        project_uuid, extension_type, file_ext)
