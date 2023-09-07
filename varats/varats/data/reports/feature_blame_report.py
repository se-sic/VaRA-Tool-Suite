"""Module for StructuralFeatureBlameReport and DataflowFeatureBlameReport."""

import re
import typing as tp
from pathlib import Path

import yaml

from varats.base.version_header import VersionHeader
from varats.data.reports.blame_report import BlameReportMetaData
from varats.data.reports.feature_analysis_report import (
    FeatureAnalysisReportMetaData,
)
from varats.report.report import BaseReport
from varats.utils.git_util import CommitRepoPair


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
        return br_regex.search(self.__feature) is not None


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

    @property
    def meta_data(self) -> FeatureBlameReportMetaData:
        """Access the meta data that was gathered with the
        ``StructuralFeatureBlameReport``."""
        return self.__meta_data

    @property
    def commit_feature_interactions(
        self
    ) -> tp.List[StructuralCommitFeatureInteraction]:
        """Return all structural cfis."""
        return self.__commit_feature_interactions


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

    @property
    def feature(self) -> str:
        """The feature of this cfi."""
        return self.__feature

    @property
    def commit(self) -> tp.List[CommitRepoPair]:
        """commit of this cfi."""
        return self.__commits

    def is_terminator(self) -> bool:
        br_regex = re.compile(r'(br( i1 | label ))|(switch i\d{1,} )')
        return br_regex.search(self.__feature) is not None


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
                .create_blame_report_meta_data(next(documents))

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

    @property
    def meta_data(self) -> FeatureBlameReportMetaData:
        """Access the meta data that was gathered with the
        ``DataflowFeatureBlameReport``."""
        return self.__meta_data

    @property
    def commit_feature_interactions(
        self
    ) -> tp.List[DataflowCommitFeatureInteraction]:
        """Return all dataflow-based cfis."""
        return self.__commit_feature_interactions
