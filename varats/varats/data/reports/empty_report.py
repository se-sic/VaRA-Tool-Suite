"""Empty report implementation for testing."""

from varats.report.report import BaseReport, FileStatusExtension, ReportFilename
from varats.utils.git_util import ShortCommitHash


class EmptyReport(BaseReport, shorthand="EMPTY", file_type="txt"):
    """
    An empty report for testing.

    Nothing gets printed into the report and the result file has no file type.
    """
