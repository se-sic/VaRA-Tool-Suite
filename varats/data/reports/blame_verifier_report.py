"""Module for a BlameVerifierReport."""
import re
import warnings
from enum import Enum
from pathlib import Path

from varats.data.report import BaseReport, MetaReport, FileStatusExtension


class ResultRegexForBlameVerifier(Enum):
    SUCCESSES = r"\(\d+/"
    FAILURES = r"\(\d+/\d+\)"
    TOTAL = r"/\d+\)"
    UNDETERMINED = r"\d+ could not be determined"


class BlameVerifierReportMixin(BaseReport):

    SHORTHAND = 'BVR_Mixin'

    @staticmethod
    def get_file_name(
        project_name: str,
        binary_name: str,
        project_version: str,
        project_uuid: str,
        extension_type: FileStatusExtension,
        file_ext: str = ".txt"
    ) -> str:
        pass

    @staticmethod
    def parse_verifier_results(
        path: Path, result_regex: ResultRegexForBlameVerifier
    ) -> int:
        """
        Parses the number of successful, failed, undetermined or total
        comparisons from a BlameMDVerifier result file.

        Args:
            path: The path to the result file
            result_regex: The specified result regex, which is looked for. Is
            (Enum: SUCCESSFUL, FAILURES, UNDETERMINED, TOTAL).

        Returns:
            Number of either successful, failed, undetermined or total
            comparisons
        """
        with open(path, 'r') as file:
            pattern = re.compile(result_regex.value)

            for line in file:
                result = pattern.search(line)

                if result is not None:
                    result_str = result.group()

                    # Calc failures from parsed total comparisons and successes
                    if result_regex is ResultRegexForBlameVerifier.FAILURES:
                        succs = re.search(
                            ResultRegexForBlameVerifier.SUCCESSES.value,
                            result_str
                        )
                        total = re.search(
                            ResultRegexForBlameVerifier.TOTAL.value, result_str
                        )

                        if succs is None:
                            raise RuntimeError(
                                f"The successful "
                                f"comparisons could not be "
                                f"parsed. Were {succs}."
                            )

                        if total is None:
                            raise RuntimeError(
                                f"The total "
                                f"comparisons could not be "
                                f"parsed. Were {total}."
                            )

                        succs_str = re.sub("[^0-9]", "", succs.group())
                        total_str = re.sub("[^0-9]", "", total.group())

                        return int(total_str) - int(succs_str)

                    # Return number of successes, total or undetermined
                    # comparisons
                    return int(re.sub("[^0-9]", "", result_str))

            if result is None and result_regex is \
                    ResultRegexForBlameVerifier.UNDETERMINED:
                warnings.warn(
                    f"The number of undetermined comparisons is either 0 or "
                    f"could not be parsed from the file: {path}. Returning 0.",
                    RuntimeWarning
                )
                return 0

            raise RuntimeError(
                f"The specified parsing regex could not be found "
                f"in the file: {path}"
            )


class BlameVerifierReportNoOpt(BlameVerifierReportMixin):
    """A BlameVerifierReport containing the filtered results of the chosen
    verifier-options, e.g., the diff of VaRA-hashes and debug-hashes, without
    any compilation optimization."""

    SHORTHAND = 'BVR_NoOpt'
    FILE_TYPE = 'txt'

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
        return MetaReport.get_file_name(
            BlameVerifierReportNoOpt.SHORTHAND, project_name, binary_name,
            project_version, project_uuid, extension_type, file_ext
        )


class BlameVerifierReportOpt(BlameVerifierReportMixin):
    """A BlameVerifierReport containing the filtered results of the chosen
    verifier-options, e.g., the diff of VaRA-hashes and debug-hashes, with
    compilation optimization."""

    SHORTHAND = 'BVR_Opt'
    FILE_TYPE = 'txt'

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
        return MetaReport.get_file_name(
            BlameVerifierReportOpt.SHORTHAND, project_name, binary_name,
            project_version, project_uuid, extension_type, file_ext
        )
