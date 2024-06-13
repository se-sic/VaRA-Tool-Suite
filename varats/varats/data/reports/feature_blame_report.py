"""Module for StructuralFeatureBlameReport and DataflowFeatureBlameReport."""

import typing as tp
from pathlib import Path

import yaml

from varats.base.version_header import VersionHeader
from varats.data.reports.feature_analysis_report import (
    FeatureAnalysisReportMetaData,
)
from varats.report.report import BaseReport
from varats.utils.git_util import CommitRepoPair


class StructuralCommitFeatureInteraction:
    """A StructuralCommitFeatureInteraction detailing the specific commit-hash
    and repo and feature and the number of instructions this structural cfi
    occurs in."""

    def __init__(
        self, num_instructions: int, features: tp.List[str],
        commit: CommitRepoPair
    ) -> None:
        self.__num_instructions = num_instructions
        self.__features = features
        self.__commit = commit

    @staticmethod
    def create_commit_feature_interaction(
        raw_inst_entry: tp.Dict[str, tp.Any]
    ) -> "StructuralCommitFeatureInteraction":
        """Creates a `StructuralCommitFeatureInteraction` entry from the
        corresponding yaml document section."""
        num_instructions = int(raw_inst_entry["num-instructions"])
        features: tp.List[str] = [
            str(feature) for feature in raw_inst_entry["features"]
        ]
        commit: CommitRepoPair = CommitRepoPair(
            (raw_inst_entry["commit-repo-pair"])["commit"],
            (raw_inst_entry["commit-repo-pair"])["repository"],
        )
        return StructuralCommitFeatureInteraction(
            num_instructions, features, commit
        )

    @property
    def num_instructions(self) -> int:
        """number of instructions the specified cfi occurs in."""
        return self.__num_instructions

    @property
    def features(self) -> tp.List[str]:
        """The features of this cfi."""
        return self.__features

    @property
    def commit(self) -> CommitRepoPair:
        """commit of this cfi."""
        return self.__commit


class FeatureBlameReportMetaData(FeatureAnalysisReportMetaData):
    pass


class StructuralFeatureBlameReport(
    BaseReport, shorthand="SFBR", file_type="yaml"
):
    """Data class that gives access to a loaded structural feature blame
    report."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)

        with open(path, "r") as stream:
            documents = yaml.load_all(stream, Loader=yaml.CLoader)
            version_header = VersionHeader(next(documents))
            version_header.raise_if_not_type("StructuralFeatureBlameReport")
            version_header.raise_if_version_is_less_than(1)

            self.__meta_data = (
                FeatureBlameReportMetaData.
                create_feature_analysis_report_meta_data(next(documents))
            )

            raw_feature_blame_report = next(documents)

            self.__commit_feature_interactions = [
                StructuralCommitFeatureInteraction.
                create_commit_feature_interaction(cfi)
                for cfi in raw_feature_blame_report[
                    "structural-commit-feature-interactions"]
            ]

    @property
    def meta_data(self) -> FeatureAnalysisReportMetaData:
        """Access the meta data that was gathered with the
        ``StructuralFeatureBlameReport``."""
        return self.__meta_data

    @property
    def commit_feature_interactions(
        self,
    ) -> tp.List[StructuralCommitFeatureInteraction]:
        """Return all structural cfis."""
        return self.__commit_feature_interactions


##### DATAFLOW #####


class DataflowCommitFeatureInteraction:
    """A DataflowCommitFeatureInteraction detailing the specific commit-hash and
    repo and feature this dataflow-based cfi occurs in."""

    def __init__(self, feature: str, commits: tp.List[CommitRepoPair]) -> None:
        self.__feature = feature
        self.__commits = commits

    @staticmethod
    def create_commit_feature_interaction(
        raw_inst_entry: tp.Dict[str, tp.Any]
    ) -> "DataflowCommitFeatureInteraction":
        """Creates a `DataflowCommitFeatureInteraction` entry from the
        corresponding yaml document section."""
        feature: str = str(raw_inst_entry["feature"])
        crps: tp.List[CommitRepoPair] = [
            CommitRepoPair(crp["commit"], crp["repository"])
            for crp in raw_inst_entry["commit-repo-pairs"]
        ]
        return DataflowCommitFeatureInteraction(feature, crps)

    @property
    def feature(self) -> str:
        """The feature of this cfi."""
        return self.__feature

    @property
    def commit(self) -> tp.List[CommitRepoPair]:
        """commit of this cfi."""
        return self.__commits


class DataflowFeatureBlameReport(
    BaseReport, shorthand="DFBR", file_type="yaml"
):
    """Data class that gives access to a loaded dataflow feature blame
    report."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)

        with open(path, "r") as stream:
            documents = yaml.load_all(stream, Loader=yaml.CLoader)
            version_header = VersionHeader(next(documents))
            version_header.raise_if_not_type("DataflowFeatureBlameReport")
            version_header.raise_if_version_is_less_than(1)

            self.__meta_data = (
                FeatureBlameReportMetaData.
                create_feature_analysis_report_meta_data(next(documents))
            )

            raw_feature_blame_report = next(documents)

            self.__commit_feature_interactions = [
                DataflowCommitFeatureInteraction.
                create_commit_feature_interaction(cfi) for cfi in
                raw_feature_blame_report["dataflow-commit-feature-interactions"]
            ]

    @property
    def meta_data(self) -> FeatureAnalysisReportMetaData:
        """Access the meta data that was gathered with the
        ``DataflowFeatureBlameReport``."""
        return self.__meta_data

    @property
    def commit_feature_interactions(
        self
    ) -> tp.List[DataflowCommitFeatureInteraction]:
        """Return all dataflow-based cfis."""
        return self.__commit_feature_interactions
