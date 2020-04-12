"""
Implements the basic blame report experiment. The experiment analyses a project
with VaRA's blame analysis and generates a BlameReport.
"""

import typing as tp

from plumbum import local

from benchbuild.project import Project
from benchbuild.settings import CFG as BB_CFG
import benchbuild.utils.actions as actions
from benchbuild.utils.cmd import opt, mkdir

from varats.experiments.wllvm import Extract
import varats.experiments.blame_experiment as BE
from varats.data.reports.blame_report import BlameIgnoreWhitespaceReport as BWR
from varats.data.report import FileStatusExtension as FSE
from varats.utils.experiment_util import (exec_func_with_pe_error_handler,
                                          VersionExperiment, PEErrorHandler)
from varats.experiments.blame_report_experiment import (BlameReportGeneration,
                                                        BlameReportExperiment)

class BlameIgnoreWhitespaceReportGeneration(BlameReportGeneration):  # type: ignore
    """
    Analyse a project with VaRA and generate a BlameReport.
    """

    NAME = "BlameIgnoreWhitespaceReportGeneration"

    DESCRIPTION = "Analyses the bitcode with -vara-BR of VaRA."

    REPORT_TYPE = BWR


class BlameIgnoreWhitespaceReportExperiment(BlameReportExperiment):
    """
    Generates a commit flow report (CFR) of the project(s) specified in the
    call.
    """

    NAME = "GenerateBlameIgnoreWhitespaceReport"

    REPORT_TYPE = BWR

    IGNORE_WHITESPACE = True

    REPORT_GENERATION = BlameIgnoreWhitespaceReportGeneration

