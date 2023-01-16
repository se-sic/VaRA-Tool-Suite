"""Instrumentation verifier report implementation for check if projects get
correctly instrumented."""
import typing as tp
from pathlib import Path
from zipfile import ZipFile

from varats.report.report import BaseReport


class InstrVerifierReport(BaseReport, shorthand="IVR", file_type="zip"):
    """An instrumentation verifier report for testing how well projects were
    instrumented."""

    def __init__(self, report_path: Path) -> None:
        super().__init__(report_path)

        self.__report_data = {}

        with ZipFile(report_path, "r") as archive:

            for file in archive.namelist():
                if not file.endswith(".ivr"):
                    continue

                with archive.open(file, "r") as json_file:
                    content = [
                        line.decode("utf-8").strip()
                        for line in json_file.readlines()
                    ]
                    binary_name = file.split("_")[-1].split(".")[0]

                    regions_entered = [
                        line[16:35]
                        for line in content
                        if line.startswith('Entered')
                    ]
                    regions_left = [
                        line[16:35]
                        for line in content
                        if line.startswith('Left')
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
                        wrong_leaves_begin = content.index(
                            'Wrong Leave-ID(s):'
                        ) + 1
                        unclosed_enter_begin = content.index(
                            'Unclosed Region-ID(s):'
                        ) + 1
                        wrong_leaves = content[wrong_leaves_begin:-1]
                        unclosed_regions = content[
                            unclosed_enter_begin:wrong_leaves_begin - 1]

                        if len(wrong_leaves) == 1 and wrong_leaves[0] == 'None':
                            wrong_leaves = []
                        else:
                            wrong_leaves = [
                                line.strip().split(' ')[0]
                                for line in wrong_leaves
                            ]

                        if len(unclosed_regions
                              ) == 1 and unclosed_regions[0] == 'None':
                            unclosed_regions = []
                        else:
                            unclosed_regions = [
                                line.strip().split(' ')[0]
                                for line in unclosed_regions
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

    def binaries(self) -> tp.List[str]:
        return list(self.__report_data.keys())

    def num_enters_total(self) -> int:
        return sum(
            len(data['regions_entered'])
            for _, data in self.__report_data.items()
        )

    def num_enters(self, binary: str) -> int:
        return len(self.__report_data[binary]['regions_entered'])

    def num_leaves_total(self) -> int:
        return sum(
            len(data['regions_left']) for _, data in self.__report_data.items()
        )

    def num_leaves(self, binary: str) -> int:
        return len(self.__report_data[binary]['regions_left'])

    def num_unclosed_enters_total(self) -> int:
        return sum(
            len(data['unclosed_regions'])
            for _, data in self.__report_data.items()
        )

    def num_unclosed_enters(self, binary: str) -> int:
        return len(self.__report_data[binary]['unclosed_regions'])

    def num_unentered_leaves_total(self) -> int:
        return sum(
            len(data['wrong_leaves']) for _, data in self.__report_data.items()
        )

    def num_unentered_leaves(self, binary: str) -> int:
        return len(self.__report_data[binary]['wrong_leaves'])

    def states(self) -> tp.Dict[str, str]:
        return {
            binary: data['state']  # type: ignore
            for binary, data in self.__report_data.items()
        }

    def state(self, binary: str) -> str:
        return self.__report_data[binary]['state']  # type: ignore
