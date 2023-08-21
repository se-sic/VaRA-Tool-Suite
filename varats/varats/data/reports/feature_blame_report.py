"""Module for StructuralFeatureBlameReport and DataflowFeatureBlameReport."""

import re
import typing as tp
from pathlib import Path

import pandas as pd
import yaml
from git import Repo

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


def generate_feature_scfi_data(
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
    rows = [[feature_data[0], feature_data[1][0], feature_data[1][1]]
            for feature_data in features_cfi_data.items()]
    return pd.DataFrame(
        rows, columns=["feature", "num_interacting_commits", "feature_scope"]
    )


def generate_feature_author_scfi_data(
    SFBR: StructuralFeatureBlameReport, path: Path
) -> pd.DataFrame:
    # {feature: (authors, size)}
    features_cfi_author_data: tp.Dict[str, tp.Tuple(tp.Set[str], int)] = {}
    for SCFI in SFBR.commit_feature_interactions:
        commit_hash = SCFI.commit.commit_hash
        author = get_author(commit_hash, path)
        entry = features_cfi_author_data.get(SCFI.feature)
        if not entry:
            features_cfi_author_data.update({
                SCFI.feature: (set([author]), SCFI.num_instructions)
            })
        else:
            entry[0].add(author)
            features_cfi_author_data.update({
                SCFI.feature: (entry[0], entry[1] + SCFI.num_instructions)
            })

    rows = [[feature_data[0],
             len(feature_data[1][0]), feature_data[1][1]]
            for feature_data in features_cfi_author_data.items()]
    return pd.DataFrame(
        rows, columns=["feature", "num_implementing_authors", "feature_size"]
    )


def get_author(commit_hash: any, path: Path) -> str:
    repo = Repo(path)
    # pygit2 libgit get
    return repo.git.show("-s", "--format=Author: %an <%ae>", commit_hash)


def generate_commit_scfi_data(
    SFBR: StructuralFeatureBlameReport
) -> pd.DataFrame:
    commit_cfi_data: tp.Dict[str, int] = {}
    for SCFI in SFBR.commit_feature_interactions:
        commit: str = SCFI.commit.commit_hash
        entry = commit_cfi_data.get(commit)
        if not entry:
            commit_cfi_data.update({commit: 1})
        else:
            commit_cfi_data.update({commit: entry + 1})
    rows = [[commit_data[0], commit_data[1]]
            for commit_data in commit_cfi_data.items()]
    return pd.DataFrame(rows, columns=["commit", "num_interacting_features"])


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
) -> pd.DataFrame:
    commits_structurally_interacting_with_features: tp.Set[str] = set()
    for SFBR in SFBRs:
        for SCFI in SFBR.commit_feature_interactions:
            commits_structurally_interacting_with_features.add(
                ShortCommitHash(SCFI.commit.commit_hash).hash
            )
    # [hash, ([interacting_features], part_of_feature)]
    dfi_commit: tp.Dict[str, tp.Tuple[tp.Set[str], int]] = {}
    for DFBR in DFBRs:
        for DCFI in DFBR.commit_feature_interactions:
            for commit in DCFI.commits:
                sch: str = ShortCommitHash(commit.commit_hash).hash
                prev = dfi_commit.get(sch)
                if prev:
                    prev[0].add(DCFI.feature)
                else:
                    part_of_feature = sch in commits_structurally_interacting_with_features
                    new = (set([DCFI.feature]), part_of_feature)
                    dfi_commit.update({sch: new})
    # value 0 in third column => not part of feature
    rows_commit_dfi = [[
        commit_data[0],
        len(commit_data[1][0]), commit_data[1][1]
    ] for commit_data in dfi_commit.items()]
    counter = 0
    for _ in range(0, num_commits - len(dfi_commit)):
        rows_commit_dfi.append([f"fake_hash{counter}", 0, 0])
        counter += 1

    columns = ["commit", "num_interacting_features", "part_of_feature"]
    return pd.DataFrame(rows_commit_dfi, columns=columns)
