"""Feature Region verification Report."""

from varats.report.report import BaseReport


class RegionVerificationReport(BaseReport, shorthand="FRR", file_type="txt"):
    """
    Feature Region verification Report.

    Prints the results of the Feature Region Verification.
    """

    SHORTHAND = "FRR"
