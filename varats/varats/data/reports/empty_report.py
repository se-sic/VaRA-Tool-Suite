"""Empty report implementation for testing."""

from varats.report.report import BaseReport, FileStatusExtension, ReportFilename
from varats.utils.git_util import ShortCommitHash


class EmptyReport(BaseReport):
    """
    An empty report for testing.

    Nothing gets printed into the report and the result file has no file type.
    """

    SHORTHAND = "EMPTY"

    @classmethod
    def shorthand(cls) -> str:
        """Shorthand for this report."""
        return cls.SHORTHAND

    @staticmethod
    def get_file_name(
        experiment_shorthand: str,
        project_name: str,
        binary_name: str,
        project_revision: ShortCommitHash,
        project_uuid: str,
        extension_type: FileStatusExtension,
        file_ext: str = ".txt"
    ) -> str:
        """
        Generates a filename for a commit report without any file ending.

        Args:
            experiment_shorthand: unique shorthand of the experiment
            project_name: name of the project for which the report was generated
            binary_name: name of the binary for which the report was generated
            project_version: version of the analyzed project, i.e., commit hash
            project_uuid: benchbuild uuid for the experiment run
            extension_type: to specify the status of the generated report
            file_ext: file extension of the report file

        Returns:
            name for the report file that can later be uniquly identified
        """
        return ReportFilename.get_file_name(
            experiment_shorthand, EmptyReport.SHORTHAND, project_name,
            binary_name, project_revision, project_uuid, extension_type,
            file_ext
        )
