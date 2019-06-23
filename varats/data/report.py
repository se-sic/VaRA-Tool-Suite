"""
Report module.
"""

import typing as tp

from varats.data.commit_report import CommitReport

ReportType = tp.TypeVar("ReportType", CommitReport, CommitReport)
