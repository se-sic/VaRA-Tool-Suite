"""Module for a BlameVerifierReport."""
import logging
import re
import typing as tp
from enum import Enum
from pathlib import Path

from varats.report.report import BaseReport, ReportFilename
from varats.utils.git_util import ShortCommitHash

LOG = logging.getLogger(__name__)


class ResultRegexForBlameVerifier(Enum):
    """An enum containing the available parsing options for BlameMDVerifier
    results."""
    value: str  # pylint: disable=invalid-name

    SUCCESSES = r"\(\d+/"
    TOTAL = r"/\d+\)"
    UNDETERMINED = r"\d+ could not be determined"


class BlameVerifierReportParserMixin:
    """Mixin that implements shared functionality between different
    `BlameVerifierReports` with various extracted methods to avoid redundancy in
    its BlameVerifierReport-Subclasses, without adapting the Report
    hierarchy."""

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(**kwargs)
        self.__path = kwargs['path']
        self.__num_successes = -1
        self.__num_failures = -1
        self.__num_total = -1
        self.__num_undetermined = -1

    def parse_verifier_results(self) -> None:
        """Parses the number of successful, failed, undetermined and total
        annotations from a BlameMDVerifier result file once and saves the
        results in member variables."""
        with open(self.__path, 'r') as file:
            first_result = ResultRegexForBlameVerifier.SUCCESSES.value
            first_result_found = False

            for line in file:

                if re.search(first_result, line) is not None:
                    first_result_found = True

                if first_result_found:
                    succs = re.search(
                        ResultRegexForBlameVerifier.SUCCESSES.value, line
                    )
                    total = re.search(
                        ResultRegexForBlameVerifier.TOTAL.value, line
                    )
                    undetermined = re.search(
                        ResultRegexForBlameVerifier.UNDETERMINED.value, line
                    )

                    if succs is not None:
                        succs_str = re.sub("[^0-9]", "", succs.group())
                        self.__num_successes = int(succs_str)

                    if total is not None:
                        total_str = re.sub("[^0-9]", "", total.group())
                        self.__num_total = int(total_str)

                    if undetermined is not None:
                        undetermined_str = re.sub(
                            "[^0-9]", "", undetermined.group()
                        )
                        self.__num_undetermined = int(undetermined_str)

        if self.__num_successes == -1:
            raise RuntimeError(
                f"The number of successful annotations could not be parsed "
                f"from file: {self.__path}."
            )

        if self.__num_total == -1:
            raise RuntimeError(
                f"The number of total annotations could not be parsed from "
                f"file: {self.__path}."
            )

        if self.__num_undetermined == -1:
            LOG.info(
                f"The number of undetermined annotations is either 0 or "
                f"could not be parsed from the file: {self.__path}. "
                f"Returning 0."
            )
            self.__num_undetermined = 0

        self.__num_failures = self.__num_total - self.__num_successes

    def get_successful_annotations(self) -> int:
        return self.__num_successes

    def get_failed_annotations(self) -> int:
        return self.__num_failures

    def get_undetermined_annotations(self) -> int:
        return self.__num_undetermined

    def get_total_annotations(self) -> int:
        return self.__num_total


class BlameVerifierReportOpt(
    BlameVerifierReportParserMixin,
    BaseReport,
    shorthand="BVR_Opt",
    file_type="txt"
):
    """A BlameVerifierReport containing the filtered results of the chosen
    verifier-options, e.g., the diff of VaRA-hashes and debug-hashes, with
    compilation optimization."""

    def __init__(self, path: Path, **kwargs: tp.Any) -> None:
        kwargs['path'] = path
        super().__init__(**kwargs)
        self.parse_verifier_results()

    @property
    def head_commit(self) -> ShortCommitHash:
        """The current HEAD commit under which this BlameVerifierReportOpt was
        created."""
        return ReportFilename(Path(self.path)).commit_hash


class BlameVerifierReportNoOptTBAA(
    BlameVerifierReportParserMixin,
    BaseReport,
    shorthand="BVR_NoOpt_TBAA",
    file_type="txt"
):
    """A BlameVerifierReport containing the filtered results of the chosen
    verifier-options, e.g., the diff of VaRA-hashes and debug-hashes, without
    any compilation optimization and TBAA (type based alias analysis)
    metadata."""

    def __init__(self, path: Path, **kwargs: tp.Any) -> None:
        kwargs['path'] = path
        super().__init__(**kwargs)
        self.parse_verifier_results()

    @property
    def head_commit(self) -> ShortCommitHash:
        """The current HEAD commit under which this BlameVerifierReportNoOpt was
        created."""
        return self.filename.commit_hash
