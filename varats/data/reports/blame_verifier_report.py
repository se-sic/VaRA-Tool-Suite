"""Module for a BlameVerifierReport."""
import re
from enum import Enum
from pathlib import Path

from varats.data.report import BaseReport, MetaReport, FileStatusExtension


class ResultType(Enum):
    SUCCESSES = r"\(\d+/"
    FAILURES = r"\(\d+/\d+\)"
    TOTAL = r"/\d+\)"


class BlameVerifierReportNoOpt(BaseReport):
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

    @staticmethod
    def parse_verifier_results(path: Path, result_type: ResultType) -> int:
        """
        Parses the successful, failed or total comparisons of a
        BlameMDVerifierNoOpt result file and returns them.

        Args:
            path: The path to the result file
            result_type: The specified type, which is looked for
            (Enum: SUCCESSFUL, FAILURES, TOTAL)

        Returns:
            Number of either successful, failed or total comparisons
        """
        with open(path, 'r') as file:
            for line in file:
                result = re.search(result_type.value, line)
                if result:
                    result = result.group()

                    # Calc failures from parsed total comparisons and successes
                    if result_type is ResultType.FAILURES:
                        total = re.search(ResultType.TOTAL.value, result)
                        total = int(re.sub("[^0-9]", "", total.group()))
                        succs = re.search(ResultType.SUCCESSES.value, result)
                        succs = int(re.sub("[^0-9]", "", succs.group()))

                        return total - succs

                    # Parse number of successes or total comparisons
                    else:
                        result = int(re.sub("[^0-9]", "", result))
                        return result

            raise RuntimeError(
                f"The specified result type could not be found "
                f"in the file: {path}"
            )


class BlameVerifierReportOpt(BaseReport):
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

    @staticmethod
    def parse_verifier_results(path: Path, result_type: ResultType) -> int:
        """
        Parses the successful, failed or total comparisons of a
        BlameMDVerifierOpt result file and returns them.

        Args:
            path: The path to the result file
            result_type: The specified type, which is looked for
            (Enum: SUCCESSFUL, FAILURES, TOTAL)

        Returns:
            Number of either successful, failed or total comparisons
        """
        with open(path, 'r') as file:
            for line in file:
                result = re.search(result_type.value, line)
                if result:
                    result = result.group()

                    # Calc failures from parsed total comparisons and successes
                    if result_type is ResultType.FAILURES:
                        total = re.search(ResultType.TOTAL.value, result)
                        total = int(re.sub("[^0-9]", "", total.group()))
                        succs = re.search(ResultType.SUCCESSES.value, result)
                        succs = int(re.sub("[^0-9]", "", succs.group()))

                        return total - succs

                    # Parse number of successes or total comparisons
                    else:
                        result = int(re.sub("[^0-9]", "", result))
                        return result

            raise RuntimeError(
                f"The specified result type could not be found "
                f"in the file: {path}"
            )
