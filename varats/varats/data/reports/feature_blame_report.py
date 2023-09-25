"""Module for StructuralFeatureBlameReport and DataflowFeatureBlameReport."""

import re
import typing as tp
from pathlib import Path

import pandas as pd
import pygit2
import yaml

from varats.base.version_header import VersionHeader
from varats.data.reports.feature_analysis_report import (
    FeatureAnalysisReportMetaData,
)
from varats.report.report import BaseReport
from varats.utils.git_util import (
    CommitRepoPair,
    ShortCommitHash,
    get_author,
    FullCommitHash,
)


class StructuralCommitFeatureInteraction:
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
    ) -> "StructuralCommitFeatureInteraction":
        """Creates a `StructuralCommitFeatureInteraction` entry from the
        corresponding yaml document section."""
        num_instructions = int(raw_inst_entry["num-instructions"])
        feature: str = str(raw_inst_entry["feature"])
        commit: CommitRepoPair = CommitRepoPair(
            (raw_inst_entry["commit-repo-pair"])["commit"],
            (raw_inst_entry["commit-repo-pair"])["repository"],
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
        br_regex = re.compile(r"(br( i1 | label ))|(switch i\d{1,} )")
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

        with open(path, "r") as stream:
            documents = yaml.load_all(stream, Loader=yaml.CLoader)
            version_header = VersionHeader(next(documents))
            version_header.raise_if_not_type("StructuralFeatureBlameReport")
            version_header.raise_if_version_is_less_than(1)

            self.__meta_data = (
                FeatureBlameReportMetaData.
                create_feature_analysis_report_meta_data(next(documents))
            )

            self.__commit_feature_interactions: tp.List[
                StructuralCommitFeatureInteraction] = []
            raw_feature_blame_report = next(documents)
            for cfi in raw_feature_blame_report[
                "structural-commit-feature-interactions"]:
                new_cfi = StructuralCommitFeatureInteraction.create_commit_feature_interaction(
                    cfi
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
        self,
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
        rows, columns=["feature", "num_interacting_commits", "feature_size"]
    )


def generate_feature_author_scfi_data(
    SFBR: StructuralFeatureBlameReport, project_gits: tp.Dict[str,
                                                              pygit2.Repository]
) -> pd.DataFrame:
    # {feature: (authors, size)}
    features_cfi_author_data: tp.Dict[str, tp.Tuple(tp.Set[str], int)] = {}
    for SCFI in SFBR.commit_feature_interactions:
        commit_hash = SCFI.commit.commit_hash
        repo = SCFI.commit.repository_name
        author = get_author(commit_hash, project_gits.get(repo))
        if author is None:
            continue
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


def generate_commit_scfi_data(
    SFBR: StructuralFeatureBlameReport, code_churn_lookup
) -> pd.DataFrame:
    commit_cfi_data: tp.Dict[str, tp.Tuple[int, int]] = {}
    for SCFI in SFBR.commit_feature_interactions:
        commit_hash = SCFI.commit.commit_hash
        repository_name = SCFI.commit.repository_name
        entry = commit_cfi_data.get(commit_hash)
        if not entry:
            repo_lookup = code_churn_lookup[repository_name]
            commit_lookup = repo_lookup.get(FullCommitHash(commit_hash))
            if commit_lookup is None:
                continue
            _, insertions, _ = commit_lookup
            commit_cfi_data.update({commit_hash: (1, insertions)})
        else:
            commit_cfi_data.update({commit_hash: (entry[0] + 1, entry[1])})
    rows = [[commit_data[0], commit_data[1][0], commit_data[1][1]]
            for commit_data in commit_cfi_data.items()]
    return pd.DataFrame(
        rows, columns=["commit", "num_interacting_features", "commit_size"]
    )


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
        crps: tp.List[CommitRepoPair] = []
        for crp in raw_inst_entry["commit-repo-pairs"]:
            crps.append(CommitRepoPair(crp["commit"], crp["repository"]))
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
        br_regex = re.compile(r"(br( i1 | label ))|(switch i\d{1,} )")
        return br_regex.search(self.__commits) is not None


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

            self.__commit_feature_interactions: tp.List[
                DataflowCommitFeatureInteraction] = []
            raw_feature_blame_report = next(documents)
            for cfi in raw_feature_blame_report[
                "dataflow-commit-feature-interactions"]:
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
        self,
    ) -> tp.ValuesView[DataflowCommitFeatureInteraction]:
        """Iterate over all cfis."""
        return self.__commit_feature_interactions


def get_commits_structurally_interacting_features(
    SFBR: StructuralFeatureBlameReport,
) -> tp.Dict[str, tp.Set[str]]:
    commits_structurally_interacting_features: tp.Dict[str, tp.Set[str]] = {}
    for SCFI in SFBR.commit_feature_interactions:
        hash = ShortCommitHash(SCFI.commit.commit_hash).hash
        entry = commits_structurally_interacting_features.get(hash)
        if not entry:
            entry = set([])
        entry.add(SCFI.feature)
        commits_structurally_interacting_features.update({hash: entry})

    return commits_structurally_interacting_features


def get_commits_dataflow_interacting_features(
    SFBR: StructuralFeatureBlameReport,
    DFBR: DataflowFeatureBlameReport,
) -> tp.Dict[str, tp.Tuple[tp.Set[str], tp.Set[str], tp.Set[str]]]:
    # [hash, ([all_interacting_features], [inside_df], [outside_df])]
    dfi_commit: tp.Dict[str, tp.Tuple[tp.Set[str], tp.Set[str],
                                      tp.Set[str]]] = {}
    commits_structurally_interacting_features: tp.Dict[
        str, tp.Set[str]] = get_commits_structurally_interacting_features(SFBR)

    for DCFI in DFBR.commit_feature_interactions:
        feature = DCFI.feature
        for commit in DCFI.commits:
            sch: str = ShortCommitHash(commit.commit_hash).hash
            entry = dfi_commit.get(sch)
            structurally_interacting_features = (
                commits_structurally_interacting_features.get(sch)
            )
            if entry is None:
                entry = (set([]), set([]), set([]))
            entry[0].add(feature)
            if structurally_interacting_features is None:
                entry[2].add(feature)
            elif feature in structurally_interacting_features:
                entry[1].add(feature)
            else:
                entry[2].add(feature)
            dfi_commit.update({sch: (entry)})

    return dfi_commit


def get_features_dataflow_affecting_commits(
    SFBR: StructuralFeatureBlameReport, DFBR: DataflowFeatureBlameReport
) -> tp.Dict[str, tp.Tuple[tp.Set[CommitRepoPair], tp.Set[CommitRepoPair]]]:
    # {feature, ([interacting_commits_outside], [interacting_commits_inside])}
    dci_feature: tp.Dict[str, tp.Tuple[tp.Set[CommitRepoPair],
                                       tp.Set[CommitRepoPair]]] = {}

    commits_structurally_interacting_with_features: tp.Dict[
        str, tp.Set[str]] = get_commits_structurally_interacting_features(SFBR)

    for DCFI in DFBR.commit_feature_interactions:
        feature = DCFI.feature
        entry = dci_feature.get(feature)
        if entry is None:
            entry = (set([]), set([]))
        for commit in DCFI.commits:
            sch: str = ShortCommitHash(commit.commit_hash).hash
            structurally_interacting_features = (
                commits_structurally_interacting_with_features.get(sch)
            )
            if structurally_interacting_features is None or not (
                feature in structurally_interacting_features
            ):
                entry[0].add(commit)
            else:
                entry[1].add(commit)
        dci_feature.update({feature: entry})

    return dci_feature


def generate_commit_specific_dcfi_data(
    SFBR: StructuralFeatureBlameReport,
    DFBR: DataflowFeatureBlameReport,
    num_commits: int,
) -> pd.DataFrame:
    # [hash, ([all_interacting_features], [inside_df], [outside_df])]
    dfi_commit = get_commits_dataflow_interacting_features(SFBR, DFBR)

    rows_commit_dfi = [[
        commit_data[0],
        len(commit_data[1][0]),
        len(commit_data[1][1]),
        len(commit_data[1][2]),
    ] for commit_data in dfi_commit.items()]
    counter = 0
    for _ in range(0, num_commits - len(dfi_commit)):
        rows_commit_dfi.append([f"fake_hash{counter}", 0, 0, 0])
        counter += 1

    columns = [
        "commit",
        "num_interacting_features",
        "num_interacting_features_inside_df",
        "num_interacting_features_outside_df",
    ]
    return pd.DataFrame(rows_commit_dfi, columns=columns)


def generate_general_commit_dcfi_data(
    SFBR: StructuralFeatureBlameReport,
    DFBR: DataflowFeatureBlameReport,
    num_commits: int,
) -> pd.DataFrame:
    row = []
    commits_structurally_interacting_features: tp.Dict[
        str, tp.Set[str]] = get_commits_structurally_interacting_features(SFBR)
    num_structurally_interacting_commits = len(
        commits_structurally_interacting_features.values()
    )
    row.append(num_structurally_interacting_commits / num_commits)

    commits_dataflow_interacting_features = get_commits_dataflow_interacting_features(
        SFBR, DFBR
    )
    interacting_structurally_and_through_dataflow = 0
    # check for every structural CFI, if its respective commit and feature also interact through dataflow
    for SCFI in SFBR.commit_feature_interactions:
        commit_hash: str = ShortCommitHash(SCFI.commit.commit_hash).hash
        entry = commits_dataflow_interacting_features.get(commit_hash)
        if (not (entry is None)) and SCFI.feature in entry[0]:
            interacting_structurally_and_through_dataflow += 1

    row.append(
        interacting_structurally_and_through_dataflow /
        len(SFBR.commit_feature_interactions)
    )

    columns = [
        "fraction_commits_structurally_interacting_with_features",
        "likelihood_dataflow_interaction_when_interacting_structurally",
    ]
    return pd.DataFrame([row], columns=columns)


def generate_feature_dcfi_data(
    SFBR: StructuralFeatureBlameReport,
    DFBR: DataflowFeatureBlameReport,
) -> pd.DataFrame:
    dci_feature = get_features_dataflow_affecting_commits(SFBR, DFBR)

    feature_scfi_data = generate_feature_scfi_data(SFBR)

    rows_feature_dci = [[
        feature_data[0],
        feature_scfi_data.loc[feature_scfi_data["feature"] == feature_data[0]]
        ["feature_size"].to_numpy()[0],
        len(feature_data[1][0]),
        len(feature_data[1][1]),
    ] for feature_data in dci_feature.items()]

    columns = [
        "feature",
        "feature_size",
        "num_interacting_commits_outside_df",
        "num_interacting_commits_inside_df",
    ]
    return pd.DataFrame(rows_feature_dci, columns=columns)


def generate_feature_author_dcfi_data(
    SFBR: StructuralFeatureBlameReport, DFBR: DataflowFeatureBlameReport,
    project_gits: tp.Dict[str, pygit2.Repository]
) -> pd.DataFrame:
    dci_feature = get_features_dataflow_affecting_commits(SFBR, DFBR)

    # {feature, ([interacting_authors_outside], [interacting_authors_inside])}
    rows_feature_author_dci = []

    feature_scfi_data = generate_feature_scfi_data(SFBR)

    for feature_data in dci_feature.items():
        feature = feature_data[0]
        interacting_commits_outside = feature_data[1][0]
        interacting_authors_outside: tp.Set[str] = set([])
        for commit in interacting_commits_outside:
            commit_hash = commit.commit_hash
            repo = commit.repository_name
            author = get_author(commit_hash, project_gits.get(repo))
            if author is None:
                continue
            interacting_authors_outside.add(author)

        interacting_commits_inside = feature_data[1][1]
        interacting_authors_inside: tp.Set[str] = set([])
        for commit in interacting_commits_inside:
            commit_hash = commit.commit_hash
            repo = commit.repository_name
            author = get_author(commit_hash, project_gits.get(repo))
            if author is None:
                continue
            interacting_authors_inside.add(author)

        rows_feature_author_dci.append([
            feature,
            feature_scfi_data.loc[feature_scfi_data["feature"] ==
                                  feature_data[0]]["feature_size"].to_numpy()
            [0],
            len(interacting_authors_outside),
            len(interacting_authors_inside),
        ])

    columns = [
        "feature",
        "feature_size",
        "interacting_authors_outside",
        "interacting_authors_inside",
    ]

    return pd.DataFrame(rows_feature_author_dci, columns=columns)
