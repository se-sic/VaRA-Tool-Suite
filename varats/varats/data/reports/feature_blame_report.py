"""Module for FeatureBlameReport."""

import re
import typing as tp
from pathlib import Path

import yaml

from varats.base.version_header import VersionHeader
from varats.report.report import BaseReport
from varats.utils.git_util import CommitRepoPair


class CommitFeatureInteraction():
    """A CommitFeatureInteraction detailing the specific commit-hash and repo
    and feature and the number of instructions this cfi occurs in."""

    def __init__(
        self, num_instructions: int, feature: str, commit: CommitRepoPair
    ) -> None:
        self.__num_instructions = num_instructions
        self.__feature = feature
        self.__commit = commit

    @staticmethod
    def create_commit_feature_interaction(
        raw_inst_entry: tp.Dict[str, tp.Any]
    ) -> 'CommitFeatureInteraction':
        """Creates a `CommitFeatureInteraction` entry from the corresponding
        yaml document section."""
        num_instructions = int(raw_inst_entry['num-instructions'])
        feature: str = str(raw_inst_entry['feature'])
        commit: CommitRepoPair = CommitRepoPair(
            raw_inst_entry['commit-hash'], raw_inst_entry['commit-repo']
        )
        return CommitFeatureInteraction(num_instructions, feature, commit)

    def print(self) -> None:
        """'CommitFeatureInteraction' prints itself."""
        print("    -COMMIT FEATURE INTERACTION")
        print("      -NUM OF INSTRUCTIONS: " + str(self.__num_instructions))
        print("      -FEATURE: " + self.__feature)
        print("        -HASH: " + self.__commit.commit_hash.__str__())
        print("        -REPO: " + self.__commit.repository_name)

    @property
    def num_instructions(self) -> int:
        """number of instructions the specified cfi occurs in."""
        return self.__num_instructions

    @property
    def feature(self) -> str:
        """The feature of this cfi."""
        return self.__feature

    @property
    def commit(self) -> CommitRepoPair:
        """commit of this cfi."""
        return self.__commit

    def is_terminator(self) -> bool:
        br_regex = re.compile(r'(br( i1 | label ))|(switch i\d{1,} )')
        return br_regex.search(self.__instruction) is not None


class FeatureBlameReportMetaData():
    """Provides extra meta data about llvm::Module, which was analyzed to
    generate this ``FeatureBlameReport``."""

    def __init__(
        self, num_functions: int, num_instructions: int,
        num_br_switch_insts: int
    ) -> None:
        self.__number_of_functions_in_module = num_functions
        self.__number_of_instructions_in_module = num_instructions
        self.__number_of_branch_and_switch_ints_in_module = num_br_switch_insts

    @property
    def num_functions(self) -> int:
        """Number of functions in the analyzed llvm::Module."""
        return self.__number_of_functions_in_module

    @property
    def num_instructions(self) -> int:
        """Number of instructions processed in the analyzed llvm::Module."""
        return self.__number_of_instructions_in_module

    @property
    def num_br_switch_insts(self) -> int:
        """Number of branch and switch instructions processed in the analyzed
        llvm::Module."""
        return self.__number_of_branch_and_switch_ints_in_module

    @staticmethod
    def create_feature_analysis_report_meta_data(
        raw_document: tp.Dict[str, tp.Any]
    ) -> 'FeatureBlameReportMetaData':
        """Creates `FeatureBlameReportMetaData` from the corresponding yaml
        document."""
        num_functions = int(raw_document['funcs-in-module'])
        num_instructions = int(raw_document['insts-in-module'])
        num_br_switch_insts = int(raw_document['br-switch-insts-in-module'])

        return FeatureBlameReportMetaData(
            num_functions, num_instructions, num_br_switch_insts
        )


class FeatureBlameReport(BaseReport, shorthand="FBR", file_type="yaml"):
    """Data class that gives access to a loaded feature blame report."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)

        with open(path, 'r') as stream:
            documents = yaml.load_all(stream, Loader=yaml.CLoader)
            version_header = VersionHeader(next(documents))
            version_header.raise_if_not_type("FeatureBlameReport")
            version_header.raise_if_version_is_less_than(1)

            self.__meta_data = FeatureBlameReportMetaData \
                .create_feature_analysis_report_meta_data(next(documents))

            self.__commit_feature_interactions: tp.Dict[
                str, CommitFeatureInteraction] = {}
            raw_feature_blame_report = next(documents)
            counter: int = 1
            for cfi in raw_feature_blame_report['commit-feature-interactions']:
                key: str = "cfi_" + str(counter)
                new_cfi = (
                    CommitFeatureInteraction.create_commit_feature_interaction(
                        raw_feature_blame_report['commit-feature-interactions']
                        [key]
                    )
                )
                self.__commit_feature_interactions[key] = new_cfi
                counter = counter + 1

    def print(self) -> None:
        """'FeatureBlameReport' prints itself."""
        print("FEATURE BLAME REPORT")
        for cfi in self.__commit_feature_interactions.values():
            cfi.print()

    @property
    def meta_data(self) -> FeatureBlameReportMetaData:
        """Access the meta data that was gathered with the
        ``FeatureBlameReport``."""
        return self.__meta_data

    @property
    def commit_feature_interactions(
        self
    ) -> tp.ValuesView[CommitFeatureInteraction]:
        """Iterate over all cfis."""
        return self.__commit_feature_interactions.values()
