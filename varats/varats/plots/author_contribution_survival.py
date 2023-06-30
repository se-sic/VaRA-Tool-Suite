"""Plot for author contributions over time."""
import math
import typing as tp

from matplotlib import pyplot as plt
from matplotlib import style
from pandas import DataFrame

from varats.data.databases.author_interactions_database import (
    AuthorInteractionsDatabase,
)
from varats.data.databases.survivng_lines_database import SurvivingLinesDatabase
from varats.mapping.author_map import generate_author_map, Author
from varats.mapping.commit_map import get_commit_map
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot
from varats.plot.plots import PlotConfig, PlotGenerator
from varats.plots.surviving_commits import HeatMapPlot
from varats.project.project_util import (
    get_primary_project_source,
    get_local_project_git_path,
)
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY
from varats.utils.git_util import (
    FullCommitHash,
    create_commit_lookup_helper,
    UNCOMMITTED_COMMIT_HASH,
    CommitRepoPair,
)


def _group_data_by_author(
    project_name: str, data: DataFrame, sample_points_label: str,
    data_points_label: str, value_label: str
) -> DataFrame:
    commit_lookup_helper = create_commit_lookup_helper(project_name)
    repo = get_primary_project_source(project_name).local
    amap = generate_author_map(project_name)

    def author_data(commit_hash: str) -> tp.Optional[Author]:
        if commit_hash == UNCOMMITTED_COMMIT_HASH.hash:
            return None
        commit = commit_lookup_helper(
            CommitRepoPair(FullCommitHash(commit_hash), str(repo))
        )
        return amap.get_author(commit.author.name, commit.author.email)

    data = data.apply(
        lambda x: [
            x[sample_points_label],
            author_data(x[data_points_label]), x[value_label]
        ],
        axis=1,
        result_type='broadcast'
    )
    data = data.rename(columns={data_points_label: 'author'})
    return data.groupby(by=[sample_points_label, 'author'],
                        sort=False).sum(min_count=1).reset_index()


def get_interactions_per_author(case_study: CaseStudy) -> DataFrame:
    """Returns a DataFrame with the number of interactions per author per
    revision."""
    project_name = case_study.project_name
    amap = generate_author_map(project_name)
    data: DataFrame = AuthorInteractionsDatabase().get_data_for_project(
        project_name, [
            "revision", "author_name", "internal_interactions",
            "external_interactions"
        ], get_commit_map(project_name), case_study
    )
    data["author"] = data["author_name"].apply(amap.get_author_by_name)
    data.drop(columns=["author_name"], inplace=True)
    data["interactions"
        ] = data["internal_interactions"] + data["external_interactions"]
    return data.rename({"author_name": "author"})


def get_lines_per_author(case_study: CaseStudy):
    """Returns a DataFrame with the number of lines per author per revision."""
    project_name = case_study.project_name
    data = SurvivingLinesDatabase.get_data_for_project(
        project_name, ["revision", "commit_hash", "lines"],
        get_commit_map(project_name), case_study
    )
    return _group_data_by_author(
        project_name, data, 'revision', 'commit_hash', 'lines'
    )


def author_interactions_normalized_per_revision(
    case_study: CaseStudy, limit: int = 0
) -> DataFrame:
    """Returns a DataFrame with the number of interactions per author per
    revision normalized by the total number of interactions per revision."""
    data: DataFrame = get_interactions_per_author(case_study)
    ref_data = data.groupby(by=['revision'],
                            sort=False).interactions.sum(min_count=1)
    cmap = get_commit_map(case_study.project_name)
    data = data.apply(
        lambda x: [
            cmap.short_time_id(x['revision']),
            (
                x['internal_interactions'] / x['interactions']
                if not math.isnan(x['interactions']) else math.nan
            ),
            (
                x['external_interactions'] / x['interactions']
                if not math.isnan(x['interactions']) else math.nan
            ),
            x['author'],
            (
                x['interactions'] * 100 / ref_data[x['revision']]
                if not math.isnan(x['interactions']) else math.nan
            ),
        ],
        axis=1,
        result_type='broadcast'
    )
    data.loc[data['interactions'] < limit, 'author'] = Author(-1, "other", "")
    data = data.groupby(by=['revision', 'author'],
                        sort=False).sum(min_count=1).reset_index()
    return data


def get_interactions_per_author_normalized_per_author(case_study: CaseStudy):
    """Returns a DataFrame with the number of interactions per author per
    revision normalized by the total number of interactions per author."""
    data: DataFrame = get_interactions_per_author(case_study)
    ref_data = data.groupby(by=['author'], sort=False).amount.max()
    data = data.apply(
        lambda x: [
            x['revision'], x['author'],
            (x['amount'] * 100 / ref_data[x['author']])
            if not math.isnan(x['amount']) else math.nan
        ],
        axis=1,
        result_type='broadcast'
    )
    return data.rename(columns={'amount': 'interactions'})


def get_interactions_per_author_normalized_per_revision_wide(
    case_study: CaseStudy, limit: int = 0
):
    """
    Returns a DataFrame with the number of interactions per author per revision
    normalized by the total number of interactions per revision.

    In wide format.
    """
    data = author_interactions_normalized_per_revision(case_study, limit)
    return data.pivot(
        index="author", columns='revision', values='interactions'
    ).astype(float)


def get_lines_per_author_normalized_per_revision(
    case_study: CaseStudy, min_lines: int = 0
):
    """Returns a DataFrame with the number of lines per author per revision
    normalized by the total number of lines per revision."""
    data = get_lines_per_author(case_study)
    ref_data = data.groupby(by=['revision'], sort=False).lines.sum(min_count=1)
    cmap = get_commit_map(case_study.project_name)
    data = data.apply(
        lambda x: [
            cmap.short_time_id(x['revision']), x['author'],
            (x['lines'] * 100 / ref_data[x['revision']])
            if not math.isnan(x['lines']) else math.nan
        ],
        axis=1,
        result_type='broadcast'
    )
    data.loc[data['lines'] < min_lines, 'author'] = Author(-1, "other", "")
    data = data.groupby(by=['revision', 'author'],
                        sort=False).lines.sum(min_count=1).reset_index()
    return data


def get_lines_per_author_normalized_per_author(case_study: CaseStudy):
    """Returns a DataFrame with the number of lines per author per revision
    normalized by the maximum number of lines per author."""
    data = get_lines_per_author(case_study)
    ref_data = data.groupby(by=['author'], sort=False).lines.max()
    cmap = get_commit_map(case_study.project_name)
    data = data.apply(
        lambda x: [
            cmap.short_time_id(x['revision']), x['author'],
            (x['lines'] * 100 / ref_data[x['author']])
            if not math.isnan(x['lines']) else math.nan
        ],
        axis=1,
        result_type='broadcast'
    )
    return data


def get_author_lines_normalized_per_revision_wide(
    case_study: CaseStudy, limit: int = 0
) -> DataFrame:
    """
    Returns a DataFrame with the number of lines per author per revision
    normalized by the total number of lines per revision.

    In wide format.
    """
    data = get_lines_per_author_normalized_per_revision(case_study, limit)
    return data.pivot(index="author", columns='revision',
                      values='lines').astype(float)


def compare_lines_and_interactions_author_revision(case_study: CaseStudy):
    """
    Returns a DataFrame with the number of lines and interactions per author per
    revision normalized by the total number of lines and interactions per
    revision.

    In wide format.
    """
    lines = get_lines_per_author_normalized_per_revision(case_study)
    interactions = author_interactions_normalized_per_revision(case_study)
    data = lines.merge(interactions, how='left', on=['author', 'revision'])
    data.dropna(
        axis=0, how='any', inplace=True, subset=["lines", "interactions"]
    )
    data.insert(3, "space", math.nan)
    data = data.pivot(
        index="author",
        columns="revision",
        values=["lines", "interactions", 'space']
    )
    data = data.stack(level=0, dropna=False)
    cmap = get_commit_map(case_study.project_name)
    data = data.sort_index(axis=1, key=lambda x: x.map(cmap.short_time_id))
    return data.astype(float)


def compare_lines_and_interactions_author_author(case_study: CaseStudy):
    """Returns a DataFrame with the number of lines and interactions per author
    per revision normalized by the total number of lines and interactions per
    author."""
    lines = get_lines_per_author_normalized_per_author(case_study)
    interactions = get_interactions_per_author_normalized_per_author(case_study)
    data = lines.merge(interactions, how='left', on=['author', 'revision'])
    data.dropna(
        axis=0, how='all', inplace=True, subset=["lines", "interactions"]
    )
    data.insert(3, "space", math.nan)
    data = data.pivot(
        index="author",
        columns="revision",
        values=["lines", "interactions", 'space']
    )
    data = data.stack(level=0, dropna=False)
    cmap = get_commit_map(case_study.project_name)
    data = data.sort_index(axis=1, key=lambda x: x.map(cmap.short_time_id))
    return data.astype(float)


class ContributionPlot(Plot, plot_name=None):
    """Base class for contribution plots."""

    def __init__(
        self, plot_config: PlotConfig, data_function, **kwargs: tp.Any
    ):
        super().__init__(plot_config, **kwargs)
        self.data_function = data_function

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    def plot(self, view: bool) -> None:
        """Plots the contribution plot."""
        style.use(self.plot_config.get_dict())
        _, axis = plt.subplots(1, 1)
        case_study = self.plot_kwargs['case_study']
        data = self.data_function(case_study, 1)
        data.sort_index(
            axis=0, inplace=True, key=lambda x: x.map(lambda y: y.author_id)
        )
        data.fillna(0, inplace=True)
        data.T.plot.area(ax=axis, stacked=True)
        plt.legend(fontsize=8, bbox_to_anchor=(1, 0), loc=2, borderaxespad=0.)


class AuthorLineContribution(
    ContributionPlot, plot_name="author_line_contribution"
):
    """Contribution Plot for lines of authors."""

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    NAME = "author_line_contribution"

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any):
        super().__init__(
            plot_config, get_author_lines_normalized_per_revision_wide, **kwargs
        )


class AuthorInteractionsContribution(
    ContributionPlot, plot_name="author_interactions_contribution"
):
    """Contribution Plot for interactions of authors."""

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    NAME = "author_interactions_contribution"

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any):
        super().__init__(
            plot_config,
            get_interactions_per_author_normalized_per_revision_wide, **kwargs
        )


class AuthorContributionPlotRevision(
    HeatMapPlot, plot_name="author_contribution_plot_revision"
):
    """Heatmap Plot for lines and interactions of authors per revision."""

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    Name = "author_contribution_plot_revision"

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any):
        super().__init__(
            plot_config, compare_lines_and_interactions_author_revision,
            **kwargs
        )
        self.yticklabels = 3
        self.y_label = "Author Contribution Lines vs. Interactions"


class AuthorContributionPlotAuthor(
    HeatMapPlot, plot_name="author_contribution_plot_author"
):
    """Heatmap Plot for lines and interactions of authors per author."""

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    Name = "author_contribution_plot_author"

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any):
        super().__init__(
            plot_config, compare_lines_and_interactions_author_author, **kwargs
        )
        self.yticklabels = 3


class AuthorContributionPlotGenerator(
    PlotGenerator,
    generator_name="author-contribution",
    options=[REQUIRE_MULTI_CASE_STUDY]
):
    """Generates contribution plots."""

    def name_addition(self, i: int) -> str:
        return self.plot_kwargs["case_study"][i].project_name

    def generate(self) -> tp.List['varats.plot.plot.Plot']:
        case_studys: tp.List[CaseStudy] = self.plot_kwargs["case_study"]
        plots: tp.List[Plot] = []
        for case_study in case_studys:
            kwargs = self.plot_kwargs.copy()
            kwargs["case_study"] = case_study
            plots.append(AuthorLineContribution(self.plot_config, **kwargs))
            plots.append(
                AuthorInteractionsContribution(self.plot_config, **kwargs)
            )
        return plots
