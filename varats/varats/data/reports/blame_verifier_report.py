"""Module for a BlameVerifierReport."""
import logging
import re
import typing as tp
from enum import Enum
from pathlib import Path

from varats.report.report import BaseReport, FileStatusExtension, ReportFilename
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
        super().__init__(**kwargs)  # type: ignore
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


class BlameVerifierReportNoOpt(BlameVerifierReportParserMixin, BaseReport):
    """A BlameVerifierReport containing the filtered results of the chosen
    verifier-options, e.g., the diff of VaRA-hashes and debug-hashes, without
    any compilation optimization."""

    SHORTHAND = 'BVR_NoOpt'
    FILE_TYPE = 'txt'

    def __init__(self, path: Path, **kwargs: tp.Any) -> None:
        kwargs['path'] = path
        super().__init__(**kwargs)
        self.parse_verifier_results()

    @property
    def head_commit(self) -> ShortCommitHash:
        """The current HEAD commit under which this BlameVerifierReportNoOpt was
        created."""
        return ReportFilename(Path(self.path)).commit_hash

    @classmethod
    def shorthand(cls) -> str:
        """Shorthand for this report."""
        return cls.SHORTHAND

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
        Generates a filename for a blame verifier report with no optimization
        and '.txt' as file extension.

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
        return ReportFilename.get_file_name(
            BlameVerifierReportNoOpt.SHORTHAND, project_name, binary_name,
            project_version, project_uuid, extension_type, file_ext
        )


class BlameVerifierReportOpt(BlameVerifierReportParserMixin, BaseReport):
    """A BlameVerifierReport containing the filtered results of the chosen
    verifier-options, e.g., the diff of VaRA-hashes and debug-hashes, with
    compilation optimization."""

    SHORTHAND = 'BVR_Opt'
    FILE_TYPE = 'txt'

    def __init__(self, path: Path, **kwargs: tp.Any) -> None:
        kwargs['path'] = path
        super().__init__(**kwargs)
        self.parse_verifier_results()

    @property
    def head_commit(self) -> ShortCommitHash:
        """The current HEAD commit under which this BlameVerifierReportOpt was
        created."""
        return ReportFilename(Path(self.path)).commit_hash

    @classmethod
    def shorthand(cls) -> str:
        """Shorthand for this report."""
        return cls.SHORTHAND

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
        Generates a filename for a blame verifier report with optimization and
        '.txt' as file extension.

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
        return ReportFilename.get_file_name(
            BlameVerifierReportOpt.SHORTHAND, project_name, binary_name,
            project_version, project_uuid, extension_type, file_ext
        )


class BlameVerifierReportNoOptTBAA(BlameVerifierReportParserMixin, BaseReport):
    """A BlameVerifierReport containing the filtered results of the chosen
    verifier-options, e.g., the diff of VaRA-hashes and debug-hashes, without
    any compilation optimization and TBAA (type based alias analysis)
    metadata."""

    SHORTHAND = 'BVR_NoOpt_TBAA'
    FILE_TYPE = 'txt'

    def __init__(self, path: Path, **kwargs: tp.Any) -> None:
        kwargs['path'] = path
        super().__init__(**kwargs)
        self.parse_verifier_results()

    @property
    def head_commit(self) -> ShortCommitHash:
        """The current HEAD commit under which this BlameVerifierReportNoOpt was
        created."""
        return self.filename.commit_hash

    @classmethod
    def shorthand(cls) -> str:
        """Shorthand for this report."""
        return cls.SHORTHAND

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
        Generates a filename for a blame verifier report with no optimization
        and '.txt' as file extension.

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
        return ReportFilename.get_file_name(
            BlameVerifierReportNoOptTBAA.SHORTHAND, project_name, binary_name,
            project_version, project_uuid, extension_type, file_ext
        )
