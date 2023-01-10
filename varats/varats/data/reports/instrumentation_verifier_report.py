"""Instrumentation verifier report implementation for checkif if projects get
correctly instrumented."""
from pathlib import Path
from zipfile import ZipFile

from varats.report.report import BaseReport


class InstrVerifierReport(BaseReport, shorthand="IVR", file_type="txt"):
    """An instrumentation verifier report for testing how well projects were
    instrumented."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)

        self.__report_data = {}

        archive = ZipFile(path, "r")

        for file in archive.namelist():
            if not file.endswith(".json"):
                continue

            with archive.open(file, "r") as json_file:
                content = [
                    line.decode("utf-8") for line in json_file.readlines()
                ]
                binary_name = file.split("_")[-1].split(".")[0]

                regions_entered = [
                    line[16:35]
                    for line in content
                    if line.startswith('Entered')
                ]
                regions_left = [
                    line[16:35] for line in content if line.startswith('Left')
                ]
                state = [
                    line.split(' ')[1]
                    for line in content
                    if line.startswith('Finalization')
                ][0]

                unique_regions_entered = set(regions_entered)
                unique_regions_left = set(regions_left)
                regions_encountered = unique_regions_entered.union(
                    unique_regions_left
                )

                if state == "Failure":
                    wrong_leaves = content[content.index('Wrong Leave-ID(s):') +
                                           1:-1]
                    unclosed_regions = content[
                        content.index('Unclosed Region-ID(s):') +
                        1:content.index('Wrong Leave-ID(s):')]

                    if len(wrong_leaves) == 1 and wrong_leaves[0] == 'None':
                        wrong_leaves = []
                    else:
                        wrong_leaves = [line[2:21] for line in wrong_leaves]

                    if len(unclosed_regions
                          ) == 1 and unclosed_regions[0] == 'None':
                        unclosed_regions = []
                    else:
                        unclosed_regions = [
                            line[2:21] for line in unclosed_regions
                        ]

                self.__report_data[binary_name] = {
                    'regions_entered':
                        regions_entered,
                    'regions_left':
                        regions_left,
                    'state':
                        state,
                    'unique_regions_entered':
                        unique_regions_entered,
                    'unique_regions_left':
                        unique_regions_left,
                    'regions_encountered':
                        regions_encountered,
                    'wrong_leaves':
                        wrong_leaves if state == "Failure" else [],
                    'unclosed_regions':
                        unclosed_regions if state == "Failure" else []
                }
