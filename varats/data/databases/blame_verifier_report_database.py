"""Module for the base BlameInteractionDegreeDatabase class."""
import typing as tp
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd

from varats.data.cache_helper import build_cached_report_table
from varats.data.databases.evaluationdatabase import EvaluationDatabase
from varats.data.report import MetaReport
from varats.data.reports.blame_verifier_report import (
    BlameVerifierReportNoOpt,
    BlameVerifierReportOpt,
)
from varats.data.reports.commit_report import CommitMap
from varats.data.revisions import (
    get_failed_revisions_files,
    get_processed_revisions_files,
)
from varats.jupyterhelper.file import load_blame_report
from varats.paper.case_study import CaseStudy, get_case_study_file_name_filter
