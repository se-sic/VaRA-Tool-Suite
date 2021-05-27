from varats.report.report import BaseReport, FileStatusExtension, MetaReport

class PointsToAnalysisPerfReport(BaseReport):
    SHORTHAND = "PTAPR"
    FILE_TYPE = "json"

    @staticmethod
    def get_file_name(
        project_name: str,
        binary_name: str,
        project_version: str,
        project_uuid: str,
        extension_type: FileStatusExtension,
        file_ext: str = ".txt"
    ) -> str:
        """
        Generates a filename for a commit report with 'yaml' as file extension.

        Args:
            project_name: name of the project for which the report was generated
            binary_name: name of the binary for which the report was generated
            project_version: version of the analyzed project, i.e., commit hash
            project_uuid: benchbuild uuid for the experiment run
            extension_type: to specify the status of the generated report
            file_ext: file extension of the report file

        Returns:
            name for the report file that can later be uniquly identified
        """
        return MetaReport.get_file_name(
            PointsToAnalysisPerfReport.SHORTHAND, project_name, binary_name, project_version,
            project_uuid, extension_type, file_ext
        )

    @staticmethod
    def get_supplementary_file_name(
        project_name: str, binary_name: str, project_version: str,
        project_uuid: str, info_type: str, file_ext: str
    ) -> str:
        """
        Generates a filename for a commit report supplementary file.

        Args:
            project_name: name of the project for which the report was generated
            binary_name: name of the binary for which the report was generated
            project_version: version of the analyzed project, i.e., commit hash
            project_uuid: benchbuild uuid for the experiment run
            info_type: specifies the kind of supplementary file
            file_ext: file extension of the report file

        Returns:
            name for the supplementary report file that can later be uniquly
            identified
        """
        return BaseReport.get_supplementary_file_name(
            PointsToAnalysisPerfReport.SHORTHAND, project_name, binary_name, project_version,
            project_uuid, info_type, file_ext
        )