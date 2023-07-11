"""Module for StructuralFeatureBlameReport and DataflowFeatureBlameReport."""

import re
import typing as tp
from pathlib import Path

import pandas as pd
import yaml

from varats.base.version_header import VersionHeader
from varats.data.reports.feature_analysis_report import (
    FeatureAnalysisReportMetaData,
)
from varats.report.report import BaseReport
from varats.utils.git_util import CommitRepoPair, ShortCommitHash


class StructuralCommitFeatureInteraction():
    """A StructuralCommitFeatureInteraction detailing the specific commit-hash
    and repo and feature and the number of instructions this structural cfi
    occurs in."""

    def __init__(
        self, num_instructions: int, feature: str, commit: CommitRepoPair
    ) -> None:
        self.__num_instructions = num_instructions
        self.__feature = feature
        self.__commit = commit

    @staticmethod
    def create_commit_feature_interaction(
        raw_inst_entry: tp.Dict[str, tp.Any]
    ) -> 'StructuralCommitFeatureInteraction':
        """Creates a `StructuralCommitFeatureInteraction` entry from the
        corresponding yaml document section."""
        num_instructions = int(raw_inst_entry['num-instructions'])
        feature: str = str(raw_inst_entry['feature'])
        commit: CommitRepoPair = CommitRepoPair(
            (raw_inst_entry['commit-repo-pair'])['commit'],
            (raw_inst_entry['commit-repo-pair'])['repository']
        )
        return StructuralCommitFeatureInteraction(
            num_instructions, feature, commit
        )

    def print(self) -> None:
        """'CommitFeatureInteraction' prints itself."""
        print("    -COMMIT FEATURE INTERACTION")
        print("      -NUM OF INSTRUCTIONS: " + str(self.__num_instructions))
        print("      -FEATURE: " + self.__feature)
        print("      -HASH: " + self.__commit.commit_hash.__str__())
        print("      -REPO: " + self.__commit.repository_name)

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
        return br_regex.search(self.__num_instructions) is not None


class FeatureBlameReportMetaData(FeatureAnalysisReportMetaData):
    pass


class StructuralFeatureBlameReport(
    BaseReport, shorthand="SFBR", file_type="yaml"
):
    """Data class that gives access to a loaded structural feature blame
    report."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)

        with open(path, 'r') as stream:
            documents = yaml.load_all(stream, Loader=yaml.CLoader)
            version_header = VersionHeader(next(documents))
            version_header.raise_if_not_type("StructuralFeatureBlameReport")
            version_header.raise_if_version_is_less_than(1)

            self.__meta_data = FeatureBlameReportMetaData \
                .create_feature_analysis_report_meta_data(next(documents))

            self.__commit_feature_interactions: tp.List[
                StructuralCommitFeatureInteraction] = []
            raw_feature_blame_report = next(documents)
            for cfi in raw_feature_blame_report[
                'structural-commit-feature-interactions']:
                new_cfi = (
                    StructuralCommitFeatureInteraction.
                    create_commit_feature_interaction(cfi)
                )
                self.__commit_feature_interactions.append(new_cfi)

    def print(self) -> None:
        """'FeatureBlameReport' prints itself."""
        print("FEATURE BLAME REPORT")
        for cfi in self.__commit_feature_interactions:
            cfi.print()

    @property
    def meta_data(self) -> FeatureBlameReportMetaData:
        """Access the meta data that was gathered with the
        ``StructuralFeatureBlameReport``."""
        return self.__meta_data

    @property
    def commit_feature_interactions(
        self
    ) -> tp.ValuesView[StructuralCommitFeatureInteraction]:
        """Iterate over all cfis."""
        return self.__commit_feature_interactions


def generate_features_scfi_data(
    SFBR: StructuralFeatureBlameReport
) -> pd.DataFrame:
    features_cfi_data: tp.Dict[str, tp.Tuple(int, int)] = {}
    for SCFI in SFBR.commit_feature_interactions:
        entry = features_cfi_data.get(SCFI.feature)
        if not entry:
            features_cfi_data.update({SCFI.feature: (1, SCFI.num_instructions)})
        else:
            features_cfi_data.update({
                SCFI.feature: (entry[0] + 1, entry[1] + SCFI.num_instructions)
            })
    rows = []
    for feature_data in features_cfi_data.items():
        rows.append([feature_data[0], feature_data[1][0], feature_data[1][1]])
    return pd.DataFrame(
        rows, columns=["feature", "num_interacting_commits", "feature_scope"]
    )


##### DATAFLOW #####


class DataflowCommitFeatureInteraction():
    """A DataflowCommitFeatureInteraction detailing the specific commit-hash and
    repo and feature this dataflow-based cfi occurs in."""

    def __init__(self, feature: str, commits: tp.List[CommitRepoPair]) -> None:
        self.__feature = feature
        self.__commits = commits

    @staticmethod
    def create_commit_feature_interaction(
        raw_inst_entry: tp.Dict[str, tp.Any]
    ) -> 'DataflowCommitFeatureInteraction':
        """Creates a `DataflowCommitFeatureInteraction` entry from the
        corresponding yaml document section."""
        feature: str = str(raw_inst_entry['feature'])
        crps: tp.List[CommitRepoPair] = []
        for crp in raw_inst_entry['commit-repo-pairs']:
            crps.append(CommitRepoPair(crp['commit'], crp['repository']))
        return DataflowCommitFeatureInteraction(feature, crps)

    def print(self) -> None:
        """'CommitFeatureInteraction' prints itself."""
        print("    -COMMIT FEATURE INTERACTION")
        print("      -FEATURE: " + self.__feature)
        print("      -COMMITS: ")
        for commit in self.__commits:
            print("        -COMMIT: " + commit.commit_hash)
            print("        -REPO: " + commit.repository_name)

    @property
    def feature(self) -> str:
        """The feature of this cfi."""
        return self.__feature

    @property
    def commits(self) -> tp.List[CommitRepoPair]:
        """commits of this cfi."""
        return self.__commits

    def is_terminator(self) -> bool:
        br_regex = re.compile(r'(br( i1 | label ))|(switch i\d{1,} )')
        return br_regex.search(self.__commits) is not None


class DataflowFeatureBlameReport(
    BaseReport, shorthand="DFBR", file_type="yaml"
):
    """Data class that gives access to a loaded dataflow feature blame
    report."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)

        with open(path, 'r') as stream:
            documents = yaml.load_all(stream, Loader=yaml.CLoader)
            version_header = VersionHeader(next(documents))
            version_header.raise_if_not_type("DataflowFeatureBlameReport")
            version_header.raise_if_version_is_less_than(1)

            self.__meta_data = FeatureBlameReportMetaData \
                .create_feature_analysis_report_meta_data(next(documents))

            self.__commit_feature_interactions: tp.List[
                DataflowCommitFeatureInteraction] = []
            raw_feature_blame_report = next(documents)
            for cfi in raw_feature_blame_report[
                'dataflow-commit-feature-interactions']:
                new_cfi = (
                    DataflowCommitFeatureInteraction.
                    create_commit_feature_interaction(cfi)
                )
                self.__commit_feature_interactions.append(new_cfi)

    def print(self) -> None:
        """'DataflowFeatureBlameReport' prints itself."""
        print("DATAFLOW FEATURE BLAME REPORT")
        for cfi in self.__commit_feature_interactions:
            cfi.print()

    @property
    def meta_data(self) -> FeatureBlameReportMetaData:
        """Access the meta data that was gathered with the
        ``DataflowFeatureBlameReport``."""
        return self.__meta_data

    @property
    def commit_feature_interactions(
        self
    ) -> tp.ValuesView[DataflowCommitFeatureInteraction]:
        """Iterate over all cfis."""
        return self.__commit_feature_interactions


def generate_commit_dcfi_data(
    SFBRs: tp.List[StructuralFeatureBlameReport],
    DFBRs: tp.List[DataflowFeatureBlameReport], num_commits: int
) -> tp.Tuple[pd.DataFrame, pd.DataFrame]:
    commits_structurally_interacting_with_features: tp.Set[str] = set()
    for SFBR in SFBRs:
        for SCFI in SFBR.commit_feature_interactions:
            commits_structurally_interacting_with_features.add(
                ShortCommitHash(SCFI.commit.commit_hash).hash
            )

    dfi_commit_in_feature: tp.Dict[str, tp.Set[str]] = {}
    dfi_commit_not_in_feature: tp.Dict[str, tp.Set[str]] = {}
    for DFBR in DFBRs:
        for DCFI in DFBR.commit_feature_interactions:
            for commit in DCFI.commits:
                sch: str = ShortCommitHash(commit.commit_hash).hash
                if sch in commits_structurally_interacting_with_features:
                    prev = dfi_commit_in_feature.get(sch)
                    if prev:
                        prev.add(DCFI.feature)
                    else:
                        prev = set([DCFI.feature])
                    dfi_commit_in_feature.update({sch: prev})
                else:
                    prev = dfi_commit_not_in_feature.get(sch)
                    if prev:
                        prev.add(DCFI.feature)
                    else:
                        prev = set([DCFI.feature])
                    dfi_commit_not_in_feature.update({sch: prev})

    rows_dfi_commit_in_feature = [[
        commit_data_in_feature[0],
        len(commit_data_in_feature[1])
    ] for commit_data_in_feature in dfi_commit_in_feature.items()]
    rows_dfi_commit_not_in_feature = [[
        commit_data_not_in_feature[0],
        len(commit_data_not_in_feature[1])
    ] for commit_data_not_in_feature in dfi_commit_not_in_feature.items()]
    counter = 0
    for _ in range(
        0, num_commits - len(dfi_commit_in_feature) -
        len(dfi_commit_not_in_feature)
    ):
        rows_dfi_commit_not_in_feature.append([f"fake_hash{counter}", 0])
        counter += 1

    columns = ["commits", "num_interacting_features"]
    return pd.DataFrame(rows_dfi_commit_in_feature,
                        columns=columns), pd.DataFrame(
                            rows_dfi_commit_not_in_feature, columns=columns
                        )
