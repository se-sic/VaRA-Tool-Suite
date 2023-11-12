"""Module for StructuralFeatureBlameReport and DataflowFeatureBlameReport."""

import typing as tp
from pathlib import Path

import pandas as pd
import pygit2
import yaml
from benchbuild.utils.cmd import git
import re

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
    get_submodule_head,
    ChurnConfig,
)


class StructuralCommitFeatureInteraction:
    """A StructuralCommitFeatureInteraction detailing the specific commit-hash
    and repo and feature and the number of instructions this structural cfi
    occurs in."""

    def __init__(
        self, num_instructions: int, features: tp.List[str], commit: CommitRepoPair
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
        return StructuralCommitFeatureInteraction(num_instructions, features, commit)

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


class StructuralFeatureBlameReport(BaseReport, shorthand="SFBR", file_type="yaml"):
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
                FeatureBlameReportMetaData.create_feature_analysis_report_meta_data(
                    next(documents)
                )
            )

            raw_feature_blame_report = next(documents)

            self.__commit_feature_interactions = [
                StructuralCommitFeatureInteraction.create_commit_feature_interaction(
                    cfi
                )
                for cfi in raw_feature_blame_report[
                    "structural-commit-feature-interactions"
                ]
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


def generate_feature_scfi_data(SFBR: StructuralFeatureBlameReport) -> pd.DataFrame:
    # {ftr:
    # [[inter_commits, inter_commits_nd1, inter_commits_nd>1], [def_ftr_size, pot_ftr_size]]}
    features_cfi_data: tp.Dict[
        str,
        tp.List[tp.List[tp.Set[str], tp.Set[str], tp.Set[str]], tp.List[int, int]],
    ] = {}
    for SCFI in SFBR.commit_feature_interactions:
        commit_hash = ShortCommitHash(SCFI.commit.commit_hash).hash
        nesting_degree: int = len(SCFI.features)
        for feature in SCFI.features:
            entry = features_cfi_data.get(feature)
            if not entry:
                entry = [[set([]), set([]), set([])], [0, 0]]
            entry[0][0].add(commit_hash)
            entry[1][1] = entry[1][1] + SCFI.num_instructions
            if nesting_degree == 1:
                entry[0][1].add(commit_hash)
                entry[0][2] = entry[0][2].difference(entry[0][1])
                entry[1][0] = entry[1][0] + SCFI.num_instructions
            elif entry[0][1].isdisjoint([commit_hash]):
                entry[0][2].add(commit_hash)
            features_cfi_data.update({feature: entry})
    rows = [
        [
            feature_data[0],
            len(feature_data[1][0][0]),
            len(feature_data[1][0][1]),
            len(feature_data[1][0][2]),
            feature_data[1][1][0],
            feature_data[1][1][1],
        ]
        for feature_data in features_cfi_data.items()
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "feature",
            "num_interacting_commits",
            "num_interacting_commits_nd1",
            "num_interacting_commits_nd>1",
            "def_feature_size",
            "pot_feature_size",
        ],
    )


def generate_commit_scfi_data(
    SFBR: StructuralFeatureBlameReport, project_git_paths: tp.Dict[str, Path],
    project_name: str, head_commit: FullCommitHash
) -> pd.DataFrame:
    commit_cfi_data: tp.Dict[str, tp.Tuple[tp.List[tp.Set[str]], int]] = {}
    churn_config = ChurnConfig.create_c_style_languages_config()
    file_pattern = re.compile(
        r"|".join(
            churn_config.get_extensions_repr(prefix=r"\.", suffix=r"$")
        )
    )
    blame_regex = re.compile(r"^([0-9a-f]+)\s+(?:.+\s+)?[\d]+\) ?(.*)$")

    max_index: int = 0
    for SCFI in SFBR.commit_feature_interactions:
        features = SCFI.features
        full_commit_hash = FullCommitHash(SCFI.commit.commit_hash)
        commit_hash = ShortCommitHash(SCFI.commit.commit_hash).hash
        repo_name = SCFI.commit.repository_name
        entry = commit_cfi_data.get(commit_hash)

        if not entry:
            repo_path = project_git_paths[repo_name]
            project_git = git["-C", str(repo_path)]
            head_commit = get_submodule_head(
                project_name, repo_name, head_commit
            )

            file_names = project_git(
                "ls-tree", "--full-tree", "--name-only", "-r", full_commit_hash
            ).split("\n")
            files: tp.List[Path] = [
                repo_path / path
                for path in file_names
                if file_pattern.search(path)
            ]
            num_lines: int = 0
            for file in files:
                blame_lines: str = project_git(
                    "blame", "-w", "-s", "-l", "--root", full_commit_hash, "--",
                    str(file.relative_to(repo_path))
                )

                for line in blame_lines.strip().split("\n"):
                    sch = ShortCommitHash(blame_regex.match(line).group(1)).hash
                    if sch == commit_hash:
                        num_lines += 1
            entry = ([], num_lines)

        index = len(SCFI.features) - 1
        max_index = max(max_index, index)
        if index >= len(entry[0]):
            # add empty sets until index reached
            for _ in range(index - len(entry[0]) + 1):
                entry[0].append(set([]))

        entry[0][index].update(features)

        commit_cfi_data.update({commit_hash: entry})

    rows = []
    for key in commit_cfi_data.keys():
        val = commit_cfi_data.get(key)
        row = [key, val[1]]
        num_interacting_features_nesting_degree = [len(val[0][0])]
        features_at_lower_levels = val[0][0]
        for i in range(1, len(val[0])):
            val[0][i] = val[0][i].difference(features_at_lower_levels)
            num_interacting_features_nesting_degree.append(len(val[0][i]))
            features_at_lower_levels.update(val[0][i])
        for _ in range(max_index - len(val[0]) + 1):
            num_interacting_features_nesting_degree.append(0)
        row.append(num_interacting_features_nesting_degree)
        rows.append(row)

    return pd.DataFrame(
        rows,
        columns=["commit", "commit_size", "num_interacting_features"],
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
    def commits(self) -> tp.List[CommitRepoPair]:
        """commits of this cfi."""
        return self.__commits


class DataflowFeatureBlameReport(BaseReport, shorthand="DFBR", file_type="yaml"):
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
                FeatureBlameReportMetaData.create_feature_analysis_report_meta_data(
                    next(documents)
                )
            )

            raw_feature_blame_report = next(documents)

            self.__commit_feature_interactions = [
                DataflowCommitFeatureInteraction.create_commit_feature_interaction(cfi)
                for cfi in raw_feature_blame_report[
                    "dataflow-commit-feature-interactions"
                ]
            ]

    @property
    def meta_data(self) -> FeatureAnalysisReportMetaData:
        """Access the meta data that was gathered with the
        ``DataflowFeatureBlameReport``."""
        return self.__meta_data

    @property
    def commit_feature_interactions(self) -> tp.List[DataflowCommitFeatureInteraction]:
        """Return all dataflow-based cfis."""
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
        entry.update(SCFI.features)
        commits_structurally_interacting_features.update({hash: entry})

    return commits_structurally_interacting_features


def get_commits_dataflow_interacting_features(
    SFBR: StructuralFeatureBlameReport,
    DFBR: DataflowFeatureBlameReport,
) -> tp.Dict[str, tp.Tuple[tp.Set[str], tp.Set[str], tp.Set[str]]]:
    # [hash, ([all_interacting_features], [inside_df], [outside_df])]
    dfi_commit: tp.Dict[str, tp.Tuple[tp.Set[str], tp.Set[str], tp.Set[str]]] = {}
    commits_structurally_interacting_features: tp.Dict[
        str, tp.Set[str]
    ] = get_commits_structurally_interacting_features(SFBR)

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
    dci_feature: tp.Dict[
        str, tp.Tuple[tp.Set[CommitRepoPair], tp.Set[CommitRepoPair]]
    ] = {}

    commits_structurally_interacting_with_features: tp.Dict[
        str, tp.Set[str]
    ] = get_commits_structurally_interacting_features(SFBR)

    for DCFI in DFBR.commit_feature_interactions:
        feature = DCFI.feature
        # z_suffix,force doesn't exist in new sfbr
        if feature == "z_suffix,force":
            continue
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

    rows_commit_dfi = [
        [
            commit_data[0],
            len(commit_data[1][0]),
            len(commit_data[1][1]),
            len(commit_data[1][2]),
        ]
        for commit_data in dfi_commit.items()
    ]
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
        str, tp.Set[str]
    ] = get_commits_structurally_interacting_features(SFBR)
    num_structurally_interacting_commits = len(
        commits_structurally_interacting_features.values()
    )
    row.append(num_structurally_interacting_commits / num_commits)

    commits_dataflow_interacting_features = get_commits_dataflow_interacting_features(
        SFBR, DFBR
    )
    interacting_structurally_and_through_dataflow = 0
    num_structural_interactions = 0
    # check for every structural CFI, if its respective commit and feature also interact through dataflow
    for commit_hash, features in commits_structurally_interacting_features.items():
        entry = commits_dataflow_interacting_features.get(commit_hash)
        num_structural_interactions += len(features)
        for feature in features:
            if (not (entry is None)) and feature in entry[0]:
                interacting_structurally_and_through_dataflow += 1

    row.append(
        interacting_structurally_and_through_dataflow / num_structural_interactions
    )

    num_commits_with_structural_interactions = 0
    num_commits_with_dataflow_interactions = 0
    num_commits_with_outside_dataflow_interactions = 0
    # check for every commit structurally interacting with features,
    # if it also interacts with features through dataflow
    for commit_hash, features in commits_structurally_interacting_features.items():
        num_commits_with_structural_interactions += 1
        entry = commits_dataflow_interacting_features.get(commit_hash)
        if not (entry is None):
            num_commits_with_dataflow_interactions += 1
            if len(entry[2]) > 0:
                num_commits_with_outside_dataflow_interactions += 1
    row.append(
        num_commits_with_dataflow_interactions
        / num_commits_with_structural_interactions
    )
    row.append(
        num_commits_with_outside_dataflow_interactions
        / num_commits_with_structural_interactions
    )

    num_commits_with_outside_dataflow_interactions = sum([
        len(entry[1][2]) > 0
        for entry in commits_dataflow_interacting_features.items()
    ])
    print(num_commits)
    row.append(
        num_commits_with_outside_dataflow_interactions
        / num_commits
    )

    interacting_through_inside_dataflow = 0
    interacting_through_outside_dataflow = 0
    num_dataflow_interactions = 0
    for _, (all, inside, outside) in commits_dataflow_interacting_features.items():
        num_dataflow_interactions += len(all)
        interacting_through_inside_dataflow += len(inside)
        interacting_through_outside_dataflow += len(outside)
    row.append(
        (
            interacting_through_inside_dataflow / num_dataflow_interactions,
            interacting_through_outside_dataflow / num_dataflow_interactions,
        )
    )

    columns = [
        "fraction_commits_structurally_interacting_with_features",
        "likelihood_dataflow_interaction_when_interacting_structurally",
        "fraction_commits_with_dataflow_interactions_given_structural_interactions",
        "fraction_commits_with_outside_dataflow_interactions_given_structural_interactions",
        "fraction_commits_with_outside_dataflow_interactions",
        "proportion_dataflow_origin_for_interactions",
    ]
    return pd.DataFrame([row], columns=columns)


def generate_feature_dcfi_data(
    SFBR: StructuralFeatureBlameReport,
    DFBR: DataflowFeatureBlameReport,
) -> pd.DataFrame:
    dci_feature = get_features_dataflow_affecting_commits(SFBR, DFBR)

    feature_scfi_data = generate_feature_scfi_data(SFBR)

    rows_feature_dci = [
        [
            feature_data[0],
            feature_scfi_data.loc[feature_scfi_data["feature"] == feature_data[0]][
                "pot_feature_size"
            ].to_numpy()[0],
            len(feature_data[1][0]),
            len(feature_data[1][1]),
        ]
        for feature_data in dci_feature.items()
    ]

    columns = [
        "feature",
        "feature_size",
        "num_interacting_commits_outside_df",
        "num_interacting_commits_inside_df",
    ]
    return pd.DataFrame(rows_feature_dci, columns=columns)


def generate_feature_author_data(
    SFBR: StructuralFeatureBlameReport,
    DFBR: DataflowFeatureBlameReport,
    project_gits: tp.Dict[str, pygit2.Repository],
) -> pd.DataFrame:
    # authors that interact with features through inside df
    # also interact with them structurally per definiton
    # {feature: (struct_authors, outside_df_authors, size)}
    feature_author_data: tp.Dict[str, tp.Tuple(tp.Set[str], tp.Set[str], int)] = {}
    for SCFI in SFBR.commit_feature_interactions:
        commit_hash = SCFI.commit.commit_hash
        repo = SCFI.commit.repository_name
        author = get_author(commit_hash, project_gits.get(repo))
        if author is None:
            continue
        for feature in SCFI.features:
            entry = feature_author_data.get(feature)
            if not entry:
                feature_author_data.update(
                    {feature: (set([author]), (set([])), SCFI.num_instructions)}
                )
            else:
                entry[0].add(author)
                feature_author_data.update(
                    {feature: (entry[0], entry[1], entry[2] + SCFI.num_instructions)}
                )

    dci_feature = get_features_dataflow_affecting_commits(SFBR, DFBR)
    for feature_data in dci_feature.items():
        feature = feature_data[0]
        entry = feature_author_data.get(feature)
        if not entry:
            continue
        interacting_commits_outside = feature_data[1][0]
        for commit in interacting_commits_outside:
            commit_hash = commit.commit_hash
            repo = commit.repository_name
            author = get_author(commit_hash, project_gits.get(repo))
            if author is None:
                continue
            entry[1].add(author)
        feature_author_data.update({feature: (entry[0], entry[1], entry[2])})

    rows = [
        [
            feature_data[0],
            len(feature_data[1][0]),
            len(feature_data[1][1]),
            len(feature_data[1][1].difference(feature_data[1][0])),
            feature_data[1][2],
        ]
        for feature_data in feature_author_data.items()
    ]

    return pd.DataFrame(
        data=rows,
        columns=[
            "feature",
            "struct_authors",
            "df_authors",
            "unique_df_authors",
            "feature_size",
        ],
    )
