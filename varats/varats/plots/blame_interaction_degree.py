"""Generate plots for the degree of blame interactions."""
import abc
import logging
import typing as tp
from itertools import product

import matplotlib.pyplot as plt
import matplotlib.style as style
import numpy as np
import pandas as pd
from matplotlib import cm

from varats.data.databases.blame_interaction_degree_database import (
    BlameInteractionDegreeDatabase,
    DegreeType,
)
from varats.mapping.commit_map import CommitMap
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plots.bug_annotation import draw_bugs
from varats.plots.cve_annotation import draw_cves
from varats.plots.repository_churn import draw_code_churn_for_revisions
from varats.project.project_util import get_project_cls_by_name

LOG = logging.getLogger(__name__)


def _filter_data_frame(
    degree_type: DegreeType, interaction_plot_df: pd.DataFrame,
    commit_map: CommitMap
) -> tp.Tuple[tp.List[str], tp.List[pd.Series]]:
    """Reduce data frame to rows that match the degree type."""
    interaction_plot_df = interaction_plot_df[interaction_plot_df.degree_type ==
                                              degree_type.value]

    degree_levels = sorted(np.unique(interaction_plot_df.degree))
    interaction_plot_df = interaction_plot_df.set_index(['revision', 'degree'])
    interaction_plot_df = interaction_plot_df.reindex(
        pd.MultiIndex.from_product(
            interaction_plot_df.index.levels,
            names=interaction_plot_df.index.names
        ),
        fill_value=0
    ).reset_index()
    # fix missing time_ids introduced by the product index
    interaction_plot_df['time_id'] = interaction_plot_df['revision'].apply(
        commit_map.short_time_id
    )
    interaction_plot_df.sort_values(by=['time_id'], inplace=True)

    sub_df_list = [
        interaction_plot_df.loc[interaction_plot_df.degree == x].fraction
        for x in degree_levels
    ]
    unique_revisions = interaction_plot_df.revision.unique()

    return unique_revisions, sub_df_list


def _filter_grouped_dataframes(
    grouped_dataframes: tp.Tuple[tp.List[pd.DataFrame],
                                 tp.List[tp.Tuple[pd.DataFrame, pd.DataFrame]]],
    commit_map: CommitMap
) -> tp.Tuple[tp.List[tp.Tuple[str, str, tp.List[str], tp.List[pd.Series]]],
              tp.List[tp.Tuple[tp.Tuple[
                  str, str, tp.List[str], tp.List[pd.Series]], tp.Tuple[
                      str, str, tp.List[str], tp.List[pd.Series]]]]]:
    dataframe_list: tp.List[pd.DataFrame] = grouped_dataframes[0]
    dataframe_tuple_list: tp.List[tp.Tuple[pd.DataFrame, pd.DataFrame]
                                 ] = grouped_dataframes[1]

    def filter_data_frame(
        df: pd.DataFrame
    ) -> tp.Tuple[str, str, tp.List[str], tp.List[pd.Series]]:
        degree_levels = sorted(np.unique(df.lib_degree))
        df = df.set_index(['revision', 'lib_degree', 'base_lib', 'inter_lib'])
        df = df.reindex(
            pd.MultiIndex.from_product(df.index.levels, names=df.index.names),
            fill_value=0
        ).reset_index()
        # fix missing time_ids introduced by the product index
        df['time_id'] = df['revision'].apply(commit_map.short_time_id)
        df.sort_values(by=['time_id'], inplace=True)

        sub_df_list = [
            df.loc[df.lib_degree == x].lib_fraction for x in degree_levels
        ]

        base_library_name = df['base_lib'][0]
        inter_library_name = df['inter_lib'][0]

        unique_revisions = df.revision.unique()

        return base_library_name, inter_library_name, unique_revisions, \
               sub_df_list

    filtered_dataframe_list: tp.List[tp.Tuple[str, str, tp.List[str],
                                              tp.List[pd.Series]]] = []
    filtered_dataframe_tuple_list: tp.List[
        tp.Tuple[tp.Tuple[str, str, tp.List[str], tp.List[pd.Series]],
                 tp.Tuple[str, str, tp.List[str], tp.List[pd.Series]]]] = []

    for dataframe in dataframe_list:
        filtered_dataframe_list.append(filter_data_frame(dataframe))

    for dataframe_tuple in dataframe_tuple_list:
        filtered_df_one = filter_data_frame(dataframe_tuple[0])
        filtered_df_two = filter_data_frame(dataframe_tuple[1])
        filtered_dataframe_tuple_list.append((filtered_df_one, filtered_df_two))

    return filtered_dataframe_list, filtered_dataframe_tuple_list


def get_grouped_dataframes(
    interaction_plot_df: pd.DataFrame
) -> tp.Tuple[tp.List[pd.DataFrame], tp.List[tp.Tuple[pd.DataFrame,
                                                      pd.DataFrame]]]:
    interaction_plot_df = interaction_plot_df[[
        'revision', 'time_id', 'base_lib', 'inter_lib', 'lib_degree',
        'lib_amount', 'lib_fraction'
    ]]
    all_base_lib_names = sorted(np.unique(interaction_plot_df.base_lib))
    all_inter_lib_names = sorted(np.unique(interaction_plot_df.inter_lib))

    def build_dataframe_tuples() -> tp.Tuple[
        tp.List[pd.DataFrame], tp.List[tp.Tuple[pd.DataFrame, pd.DataFrame]]]:

        df_list: tp.List[pd.DataFrame] = []
        df_tuple_list: tp.List[tp.Tuple[pd.DataFrame, pd.DataFrame]] = []

        # TODO: Find more efficient way to remove tuples with same values
        name_combination_list = set(
            tuple(sorted(list(tup)))
            for tup in product(all_base_lib_names, all_inter_lib_names)
        )

        for name_tuple in name_combination_list:
            df_first = interaction_plot_df[(
                interaction_plot_df[['base_lib',
                                     'inter_lib']] == list(name_tuple)
            ).all(1)]

            df_second = interaction_plot_df[(
                interaction_plot_df[['inter_lib',
                                     'base_lib']] == list(name_tuple)
            ).all(1)]

            if not df_first.empty or not df_second.empty:
                if df_first.equals(df_second) or df_second.empty:
                    df_list.append(df_first)
                else:
                    df_pair = (df_first, df_second)
                    df_tuple_list.append(df_pair)

        return df_list, df_tuple_list

    return build_dataframe_tuples()


class BlameDegree(Plot):
    """Base plot for blame degree plots."""

    @abc.abstractmethod
    def plot(self, view_mode: bool) -> None:
        """Plot the current plot to a file."""

    def _get_degree_data(self) -> pd.DataFrame:
        commit_map: CommitMap = self.plot_kwargs['get_cmap']()
        case_study = self.plot_kwargs.get('plot_case_study', None)
        project_name = self.plot_kwargs["project"]
        interaction_plot_df = \
            BlameInteractionDegreeDatabase.get_data_for_project(
                project_name, [
                    "revision", "time_id", "degree_type", "degree", "amount",
                    "fraction", "base_lib", "inter_lib", "lib_degree",
                    "lib_amount", "lib_fraction"
                ], commit_map, case_study)

        length = len(np.unique(interaction_plot_df['revision']))
        is_empty = interaction_plot_df.empty

        if is_empty or length == 1:
            # Need more than one data point
            raise PlotDataEmpty
        return interaction_plot_df

    def _degree_plot(
        self,
        view_mode: bool,
        degree_type: DegreeType,
        extra_plot_cfg: tp.Optional[tp.Dict[str, tp.Any]] = None,
        with_churn: bool = True
    ) -> None:
        plot_cfg = {
            'linewidth': 1 if view_mode else 0.25,
            'legend_size': 8 if view_mode else 2,
            'xtick_size': 10 if view_mode else 2,
            'lable_modif': lambda x: x,
            'legend_title': 'MISSING legend_title',
            'legend_visible': True,
            'fig_title': 'MISSING figure title',
            'edgecolor': 'black',
            'color_map': cm.get_cmap('gist_stern'),
        }
        if extra_plot_cfg is not None:
            plot_cfg.update(extra_plot_cfg)

        style.use(self.style)

        commit_map: CommitMap = self.plot_kwargs['get_cmap']()
        interaction_plot_df = self._get_degree_data()

        # TODO: differentiate plot types
        is_multi_lib_plot = True
        if is_multi_lib_plot:
            grouped_dataframes = get_grouped_dataframes(interaction_plot_df)
            filtered_dataframes = _filter_grouped_dataframes(
                grouped_dataframes, commit_map
            )
            mono_plot_degrees = []
            for dataframe in grouped_dataframes[0]:
                mono_plot_degrees.append(
                    sorted(np.unique(dataframe['lib_degree']))
                )

            multi_plot_degree_tuples: tp.List[tp.Tuple[tp.List[int],
                                                       tp.List[int]]] = []
            for dataframe_tuple in grouped_dataframes[1]:
                multi_plot_degree_tuples.append((
                    sorted(np.unique(dataframe_tuple[0]['lib_degree'])),
                    sorted(np.unique(dataframe_tuple[1]['lib_degree']))
                ))

            mono_plot_data = filtered_dataframes[0]
            multi_plot_data = filtered_dataframes[1]
        else:
            # TODO: differentiate btw. single degree plot and multi lib degree
            unique_revisions, sub_df_list = _filter_data_frame(
                degree_type, interaction_plot_df, commit_map
            )

        def generate_mono_lib_plot(
            data: tp.Tuple[str, str, tp.List[str], tp.List[pd.Series]],
            degrees: tp.List[int]
        ) -> None:

            base_lib_name = data[0]
            inter_lib_name = data[1]
            unique_revisions = data[2]
            fraction_series = data[3]

            fig = plt.figure()
            grid_spec = fig.add_gridspec(3, 1)

            if with_churn:
                main_axis = fig.add_subplot(grid_spec[:-1, :])
                main_axis.get_xaxis().set_visible(False)
                churn_axis = fig.add_subplot(grid_spec[2, :], sharex=main_axis)
                x_axis = churn_axis
            else:
                main_axis = fig.add_subplot(grid_spec[:, :])
                x_axis = main_axis

            fig.subplots_adjust(top=0.95, hspace=0.05, right=0.95, left=0.07)
            fig.suptitle(
                str(plot_cfg['fig_title']) +
                f' - Project {self.plot_kwargs["project"]} | {base_lib_name} '
                f'--> {inter_lib_name}',
                fontsize=8
            )

            main_axis.stackplot(
                unique_revisions,
                fraction_series,
                edgecolor=plot_cfg['edgecolor'],
                colors=reversed(
                    plot_cfg['color_map'](
                        np.linspace(0, 1, len(fraction_series))
                    )
                ),
                labels=map(
                    tp.cast(tp.Callable[[str], str], plot_cfg['lable_modif']),
                    degrees
                )
            )

            legend = main_axis.legend(
                title=plot_cfg['legend_title'],
                loc='upper left',
                prop={
                    'size': plot_cfg['legend_size'],
                    'family': 'monospace'
                },
            )
            plt.setp(
                legend.get_title(),
                fontsize=plot_cfg['legend_size'],
                family='monospace'
            )
            legend.set_visible(plot_cfg['legend_visible'])

            # annotate CVEs
            with_cve = self.plot_kwargs.get("with_cve", False)
            with_bugs = self.plot_kwargs.get("with_bugs", False)
            if with_cve or with_bugs:
                if "project" not in self.plot_kwargs:
                    LOG.error("Need a project to annotate bug or CVE data.")
                else:
                    project = get_project_cls_by_name(
                        self.plot_kwargs["project"]
                    )
                    if with_cve:
                        draw_cves(
                            main_axis, project, unique_revisions, plot_cfg
                        )
                    if with_bugs:
                        draw_bugs(
                            main_axis, project, unique_revisions, plot_cfg
                        )

            # draw churn subplot
            if with_churn:
                draw_code_churn_for_revisions(
                    churn_axis, self.plot_kwargs['project'],
                    self.plot_kwargs['get_cmap'](), unique_revisions
                )

            plt.setp(
                x_axis.get_yticklabels(), fontsize=8, fontfamily='monospace'
            )
            plt.setp(
                x_axis.get_xticklabels(),
                fontsize=plot_cfg['xtick_size'],
                fontfamily='monospace',
                rotation=270
            )

        def generate_multi_lib_plot(
            data: tp.Tuple[tp.Tuple[str, str, tp.List[str], tp.List[pd.Series]],
                           tp.Tuple[str, str, tp.List[str],
                                    tp.List[pd.Series]]],
            degrees: tp.Tuple[tp.List[int], tp.List[int]]
        ) -> None:

            # TODO: differentiate btw. mono plot and multi plot
            base_lib_name = data[0][0]
            inter_lib_name = data[0][1]

            unique_revisions_one = data[0][2]
            fraction_series_one = data[0][3]
            degrees_one = degrees[0]

            unique_revisions_two = data[1][2]
            fraction_series_two = data[1][3]
            degrees_two = degrees[1]

            fig = plt.figure()
            grid_spec = fig.add_gridspec(3, 1)

            if with_churn:
                main_axis = fig.add_subplot(grid_spec[:-1, :])
                main_axis.get_xaxis().set_visible(False)
                churn_axis = fig.add_subplot(grid_spec[2, :], sharex=main_axis)
                x_axis = churn_axis
            else:
                main_axis = fig.add_subplot(grid_spec[:, :])
                x_axis = main_axis

            fig.subplots_adjust(top=0.95, hspace=0.05, right=0.95, left=0.07)
            fig.suptitle(
                str(plot_cfg['fig_title']) +
                f' - Project {self.plot_kwargs["project"]} | {base_lib_name} '
                f'<--> {inter_lib_name}',
                fontsize=8
            )

            # TODO: Choose colormaps that have exlusive colors compared to
            #  each other
            # TODO: Find way to add markers like lines to area of stackplot
            first_plot, = main_axis.stackplot(
                unique_revisions_one,
                fraction_series_one,
                edgecolor=plot_cfg['edgecolor'],
                colors=cm.get_cmap('inferno')(
                    np.linspace(0, 1, len(fraction_series_two))
                ),
                # TODO (se-passau/VaRA#545): remove cast with plot config rework
                labels=map(
                    tp.cast(tp.Callable[[str], str], plot_cfg['lable_modif']),
                    degrees_one
                ),
                linewidth=plot_cfg['linewidth']
            )

            second_plot, _, = main_axis.stackplot(
                unique_revisions_two,
                fraction_series_two,
                edgecolor=plot_cfg['edgecolor'],
                colors=reversed(
                    cm.get_cmap('ocean')(
                        np.linspace(0, 1, len(fraction_series_two))
                    )
                ),
                linewidth=plot_cfg['linewidth'],
                alpha=0.3
            )

            legend_one = main_axis.legend(
                title=plot_cfg['legend_title'] +
                f" | {base_lib_name} --> {inter_lib_name}",
                loc='upper left',
                prop={
                    'size': plot_cfg['legend_size'],
                    'family': 'monospace'
                },
                handles=[first_plot]
            )
            plt.setp(
                legend_one.get_title(),
                fontsize=plot_cfg['legend_size'],
                family='monospace'
            )

            legend_two = main_axis.legend(
                title=plot_cfg['legend_title'] +
                f" | {inter_lib_name} --> {base_lib_name}",
                loc='upper right',
                prop={
                    'size': plot_cfg['legend_size'],
                    'family': 'monospace'
                },
                # TODO (se-passau/VaRA#545): remove cast with plot config rework
                labels=map(
                    tp.cast(tp.Callable[[str], str], plot_cfg['lable_modif']),
                    degrees_two
                ),
                handles=[second_plot],
            )
            plt.setp(
                legend_two.get_title(),
                fontsize=plot_cfg['legend_size'],
                family='monospace'
            )

            legend_one.set_visible(plot_cfg['legend_visible'])
            legend_two.set_visible(plot_cfg['legend_visible'])

            main_axis.add_artist(legend_one)

            # TODO: Fix disappearing labels in legends
            """
            # annotate CVEs
            with_cve = self.plot_kwargs.get("with_cve", False)
            with_bugs = self.plot_kwargs.get("with_bugs", False)
            if with_cve or with_bugs:
                if "project" not in self.plot_kwargs:
                    LOG.error("Need a project to annotate bug or CVE data.")
                else:
                    project = get_project_cls_by_name(
                        self.plot_kwargs["project"]
                    )
                    if with_cve:
                        draw_cves(
                            main_axis, project, unique_revisions, plot_cfg
                        )
                    if with_bugs:
                        draw_bugs(
                            main_axis, project, unique_revisions, plot_cfg
                        )

            # draw churn subplot
            if with_churn:
                draw_code_churn_for_revisions(
                    churn_axis, self.plot_kwargs['project'],
                    self.plot_kwargs['get_cmap'](), unique_revisions
                )

            plt.setp(
                x_axis.get_yticklabels(), fontsize=8, fontfamily='monospace'
            )
            plt.setp(
                x_axis.get_xticklabels(),
                fontsize=plot_cfg['xtick_size'],
                fontfamily='monospace',
                rotation=270
            )
        """

        # TODO: Generate one plot for each plot date
        #for idx, data in enumerate(mono_plot_data):
        generate_mono_lib_plot(mono_plot_data[1], degrees=mono_plot_degrees[1])

        #for idx, data in enumerate(multi_plot_data):
        #    generate_multi_lib_plot(data, degrees=multi_plot_degree_tuples[idx])

    def _calc_missing_revisions(
        self, degree_type: DegreeType, boundary_gradient: float
    ) -> tp.Set[str]:
        """
        Select a set of revisions based on the gradients of the degree levels
        between revisions.

        Args:
            degree_type: the degree type to consider for gradient calculation
            boundary_gradient: the gradient threshold that needs to be exceeded
                               to include a new revision

        Returns:
            a set of revisions sampled between revisions with unusually large
            changes in degree distribution
        """
        commit_map: CommitMap = self.plot_kwargs['get_cmap']()
        interaction_plot_df = self._get_degree_data()
        unique_revisions, sub_df_list = _filter_data_frame(
            degree_type, interaction_plot_df, commit_map
        )

        def head_cm_neighbours(lhs_cm: str, rhs_cm: str) -> bool:
            return commit_map.short_time_id(
                lhs_cm
            ) + 1 == commit_map.short_time_id(rhs_cm)

        new_revs: tp.Set[str] = set()

        # build a dataframe with revision as index and degree values as columns
        # the cells contain the degree frequencies per revision
        df = pd.concat([
            series.reset_index(drop=True) for series in sub_df_list
        ],
                       axis=1)
        df["revision"] = unique_revisions
        df = df.set_index("revision")
        df_iter = df.iterrows()
        last_revision, last_row = next(df_iter)
        for revision, row in df_iter:
            # compute gradient for each degree value and see if any gradient
            # exceeds threshold
            gradient = abs(row - last_row)
            if any(gradient > boundary_gradient):
                lhs_cm = last_revision
                rhs_cm = revision
                if head_cm_neighbours(lhs_cm, rhs_cm):
                    print(
                        "Found steep gradient between neighbours " +
                        "{lhs_cm} - {rhs_cm}: {gradient}".format(
                            lhs_cm=lhs_cm,
                            rhs_cm=rhs_cm,
                            gradient=round(max(gradient), 5)
                        )
                    )
                else:
                    print(
                        "Unusual gradient between " +
                        "{lhs_cm} - {rhs_cm}: {gradient}".format(
                            lhs_cm=lhs_cm,
                            rhs_cm=rhs_cm,
                            gradient=round(max(gradient), 5)
                        )
                    )
                    new_rev_id = round((
                        commit_map.short_time_id(lhs_cm) +
                        commit_map.short_time_id(rhs_cm)
                    ) / 2.0)
                    new_rev = self.plot_kwargs['cmap'].c_hash(new_rev_id)
                    print(
                        "-> Adding {rev} as new revision to the sample set".
                        format(rev=new_rev)
                    )
                    new_revs.add(new_rev)
                print()
            last_revision = revision
            last_row = row
        return new_revs


class BlameInteractionDegree(BlameDegree):
    """Plotting the degree of blame interactions."""

    NAME = 'b_interaction_degree'

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'legend_title': 'Interaction degrees',
            'fig_title': 'Blame interactions'
        }
        self._degree_plot(view_mode, DegreeType.interaction, extra_plot_cfg)

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        return self._calc_missing_revisions(
            DegreeType.interaction, boundary_gradient
        )


class BlameAuthorDegree(BlameDegree):
    """Plotting the degree of authors for all blame interactions."""

    NAME = 'b_author_degree'

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'legend_title': 'Author interaction degrees',
            'fig_title': 'Author blame interactions'
        }
        self._degree_plot(view_mode, DegreeType.author, extra_plot_cfg)

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        return self._calc_missing_revisions(
            DegreeType.author, boundary_gradient
        )


class BlameMaxTimeDistribution(BlameDegree):
    """Plotting the degree of max times differences for all blame
    interactions."""

    NAME = 'b_maxtime_distribution'

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'legend_visible': False,
            'fig_title': 'Max time distribution',
            'edgecolor': None,
        }
        self._degree_plot(view_mode, DegreeType.max_time, extra_plot_cfg)

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        return self._calc_missing_revisions(
            DegreeType.max_time, boundary_gradient
        )


class BlameAvgTimeDistribution(BlameDegree):
    """Plotting the degree of avg times differences for all blame
    interactions."""

    NAME = 'b_avgtime_distribution'

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'legend_visible': False,
            'fig_title': 'Average time distribution',
            'edgecolor': None,
        }
        self._degree_plot(view_mode, DegreeType.avg_time, extra_plot_cfg)

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        return self._calc_missing_revisions(
            DegreeType.avg_time, boundary_gradient
        )
