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

        degree_levels = sorted(np.unique(df.degree))
        df = df.set_index(['revision', 'degree', 'base_lib', 'inter_lib'])
        df = df.reindex(
            pd.MultiIndex.from_product(df.index.levels, names=df.index.names),
            fill_value=0
        ).reset_index()
        # fix missing time_ids introduced by the product index
        df['time_id'] = df['revision'].apply(commit_map.short_time_id)
        df.sort_values(by=['time_id'], inplace=True)

        sub_df_list = [df.loc[df.degree == x].fraction for x in degree_levels]

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


def get_distinct_base_lib_names(df: pd.DataFrame) -> tp.List[str]:
    return sorted(np.unique([str(base_lib) for base_lib in df.base_lib]))


def get_distinct_inter_lib_names(df: pd.DataFrame) -> tp.List[str]:
    return sorted(np.unique([str(inter_lib) for inter_lib in df.inter_lib]))


def get_grouped_dataframes(
    interaction_plot_df: pd.DataFrame
) -> tp.Tuple[tp.List[pd.DataFrame], tp.List[tp.Tuple[pd.DataFrame,
                                                      pd.DataFrame]]]:

    interaction_plot_df = interaction_plot_df[interaction_plot_df.degree_type ==
                                              DegreeType.interaction.value]

    all_base_lib_names: tp.List[str] = sorted(
        np.unique([str(base_lib) for base_lib in interaction_plot_df.base_lib])
    )
    all_inter_lib_names: tp.List[str] = sorted(
        np.unique([
            str(inter_lib) for inter_lib in interaction_plot_df.inter_lib
        ])
    )

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
                if df_second.empty:
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
                    "revision", "time_id", "degree_type", "base_lib",
                    "inter_lib", "degree", "amount", "fraction"
                ], commit_map, case_study)

        length = len(np.unique(interaction_plot_df['revision']))
        is_empty = interaction_plot_df.empty

        if is_empty or length == 1:
            # Need more than one data point
            raise PlotDataEmpty
        return interaction_plot_df

    def _fraction_overview_plot(
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
            'color_map': cm.get_cmap('tab10')
        }
        if extra_plot_cfg is not None:
            plot_cfg.update(extra_plot_cfg)

        style.use(self.style)

        df = self._get_degree_data()
        df = df[df.degree_type == degree_type.value]
        df.sort_values(by=['time_id'], inplace=True)
        df.reset_index(inplace=True)
        revision_df = pd.DataFrame(df["revision"])
        unique_revisions = list(revision_df["revision"].unique())
        grouped_df: pd.DataFrame = df.groupby(['revision'])

        dataframes_per_revision: tp.Dict[str, pd.DataFrame] = {}
        total_amount_per_revision: tp.Dict[str, int] = {}

        for revision in unique_revisions:
            dataframes_per_revision[revision] = grouped_df.get_group(revision)

        base_lib_names_per_revision: tp.Dict[str, tp.List[str]] = {}
        inter_lib_names_per_revision: tp.Dict[str, tp.List[str]] = {}

        for revision in unique_revisions:
            total_amount_per_revision[revision] = dataframes_per_revision[
                revision].sum().amount
            base_lib_names_per_revision[revision] = get_distinct_base_lib_names(
                dataframes_per_revision[revision]
            )
            inter_lib_names_per_revision[revision
                                        ] = get_distinct_inter_lib_names(
                                            dataframes_per_revision[revision]
                                        )

        base_lib_fractions: tp.Dict[str, tp.List[float]] = {}
        inter_lib_fractions: tp.Dict[str, tp.List[float]] = {}
        base_plot_data: tp.List[tp.List] = []
        inter_plot_data: tp.List[tp.List] = []

        for revision in unique_revisions:
            for base_name in base_lib_names_per_revision[revision]:
                if base_name not in base_lib_fractions:
                    base_lib_fractions[base_name] = []

                current_fraction = np.divide(
                    dataframes_per_revision[revision].loc[
                        dataframes_per_revision[revision].base_lib == base_name
                    ].amount.sum(), total_amount_per_revision[revision]
                )
                base_lib_fractions[base_name].append(current_fraction)

            for inter_name in inter_lib_names_per_revision[revision]:
                if inter_name not in inter_lib_fractions:
                    inter_lib_fractions[inter_name] = []

                current_fraction = np.divide(
                    dataframes_per_revision[revision].loc[
                        dataframes_per_revision[revision].inter_lib ==
                        inter_name].amount.sum(),
                    total_amount_per_revision[revision]
                )
                inter_lib_fractions[inter_name].append(current_fraction)

        base_plot_data = [
            base_fraction for base_fraction in base_lib_fractions.values()
        ]

        inter_plot_data = [
            inter_fraction for inter_fraction in inter_lib_fractions.values()
        ]

        def generate_fraction_overview_plot() -> None:
            fig = plt.figure()
            grid_spec = fig.add_gridspec(3, 1)

            if with_churn:
                out_axis = fig.add_subplot(grid_spec[0, :])
                out_axis.get_xaxis().set_visible(False)
                in_axis = fig.add_subplot(grid_spec[1, :])
                in_axis.get_xaxis().set_visible(False)
                churn_axis = fig.add_subplot(grid_spec[-1, :], sharex=out_axis)
                x_axis = churn_axis
            else:
                out_axis = fig.add_subplot(grid_spec[0, :])
                in_axis = fig.add_subplot(grid_spec[1, :])
                x_axis = in_axis

            fig.subplots_adjust(top=0.95, hspace=0.05, right=0.95, left=0.07)
            fig.suptitle(
                str(plot_cfg['fig_title']) +
                f' - Project {self.plot_kwargs["project"]}',
                fontsize=8
            )
            cm_length = max(len(base_lib_fractions), len(inter_lib_fractions))
            colormap = plot_cfg['color_map'](np.linspace(0, 1, cm_length))

            outgoing_plot_lines = []
            ingoing_plot_lines = []
            alpha = 0.7

            outgoing_plot_lines += out_axis.stackplot(
                unique_revisions,
                base_plot_data,
                linewidth=plot_cfg['linewidth'],
                colors=colormap,
                edgecolor=plot_cfg['edgecolor'],
                alpha=alpha
            )

            legend_out = out_axis.legend(
                handles=outgoing_plot_lines,
                title=plot_cfg['legend_title'] + f" | Outgoing interactions",
                # TODO (se-passau/VaRA#545): remove cast with plot config rework
                labels=map(
                    tp.cast(tp.Callable[[str], str], plot_cfg['lable_modif']),
                    base_lib_fractions
                ),
                loc='upper left',
                prop={
                    'size': plot_cfg['legend_size'],
                    'family': 'monospace'
                }
            )
            plt.setp(
                legend_out.get_title(),
                fontsize=plot_cfg['legend_size'],
                family='monospace',
            )
            out_axis.add_artist(legend_out)
            legend_out.set_visible(plot_cfg['legend_visible'])

            ingoing_plot_lines += in_axis.stackplot(
                unique_revisions,
                inter_plot_data,
                linewidth=plot_cfg['linewidth'],
                colors=colormap,
                edgecolor=plot_cfg['edgecolor'],
                alpha=alpha
            )
            legend_in = in_axis.legend(
                handles=ingoing_plot_lines,
                title=plot_cfg['legend_title'] + f" | Ingoing interactions",
                # TODO (se-passau/VaRA#545): remove cast with plot config rework
                labels=map(
                    tp.cast(tp.Callable[[str], str], plot_cfg['lable_modif']),
                    inter_lib_fractions
                ),
                loc='upper left',
                prop={
                    'size': plot_cfg['legend_size'],
                    'family': 'monospace'
                }
            )
            plt.setp(
                legend_in.get_title(),
                fontsize=plot_cfg['legend_size'],
                family='monospace',
            )
            in_axis.add_artist(legend_in)
            legend_in.set_visible(plot_cfg['legend_visible'])

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
                        draw_cves(in_axis, project, unique_revisions, plot_cfg)
                    if with_bugs:
                        draw_bugs(in_axis, project, unique_revisions, plot_cfg)

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

        generate_fraction_overview_plot()

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
        unique_revisions, sub_df_list = _filter_data_frame(
            degree_type, interaction_plot_df, commit_map
        )

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
            f' - Project {self.plot_kwargs["project"]}',
            fontsize=8
        )

        main_axis.stackplot(
            unique_revisions,
            sub_df_list,
            edgecolor=plot_cfg['edgecolor'],
            colors=reversed(
                plot_cfg['color_map'](np.linspace(0, 1, len(sub_df_list)))
            ),
            # TODO (se-passau/VaRA#545): remove cast with plot config rework
            labels=map(
                tp.cast(tp.Callable[[str], str], plot_cfg['lable_modif']),
                sorted(np.unique(interaction_plot_df['degree']))
            ),
            linewidth=plot_cfg['linewidth']
        )

        legend = main_axis.legend(
            title=plot_cfg['legend_title'],
            loc='upper left',
            prop={
                'size': plot_cfg['legend_size'],
                'family': 'monospace'
            }
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
                project = get_project_cls_by_name(self.plot_kwargs["project"])
                if with_cve:
                    draw_cves(main_axis, project, unique_revisions, plot_cfg)
                if with_bugs:
                    draw_bugs(main_axis, project, unique_revisions, plot_cfg)

        # draw churn subplot
        if with_churn:
            draw_code_churn_for_revisions(
                churn_axis, self.plot_kwargs['project'],
                self.plot_kwargs['get_cmap'](), unique_revisions
            )

        plt.setp(x_axis.get_yticklabels(), fontsize=8, fontfamily='monospace')
        plt.setp(
            x_axis.get_xticklabels(),
            fontsize=plot_cfg['xtick_size'],
            fontfamily='monospace',
            rotation=270
        )

    def _multi_lib_degree_plot(
        self,
        view_mode: bool,
        extra_plot_cfg: tp.Optional[tp.Dict[str, tp.Any]] = None,
        with_churn: bool = True
    ) -> None:
        plot_cfg = {
            'linewidth': 2 if view_mode else 1,
            'legend_size': 5 if view_mode else 2,
            'xtick_size': 10 if view_mode else 2,
            'lable_modif': lambda x: x,
            'legend_title': 'MISSING legend_title',
            'legend_visible': True,
            'fig_title': 'MISSING figure title',
            'edgecolor': 'black',
            'colormap_first': cm.get_cmap('autumn_r'),
            'colormap_second': cm.get_cmap('bwr_r'),
        }
        if extra_plot_cfg is not None:
            plot_cfg.update(extra_plot_cfg)

        style.use(self.style)

        commit_map: CommitMap = self.plot_kwargs['get_cmap']()
        interaction_plot_df = self._get_degree_data()

        grouped_dataframes = get_grouped_dataframes(interaction_plot_df)
        filtered_dataframes = _filter_grouped_dataframes(
            grouped_dataframes, commit_map
        )
        mono_plot_degrees = []
        for dataframe in grouped_dataframes[0]:
            mono_plot_degrees.append(sorted(np.unique(dataframe['degree'])))

        multi_plot_degree_tuples: tp.List[tp.Tuple[tp.List[int],
                                                   tp.List[int]]] = []
        for dataframe_tuple in grouped_dataframes[1]:
            multi_plot_degree_tuples.append((
                sorted(np.unique(dataframe_tuple[0]['degree'])),
                sorted(np.unique(dataframe_tuple[1]['degree']))
            ))

        mono_plot_data = filtered_dataframes[0]
        multi_plot_data = filtered_dataframes[1]

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

            lines = []
            colormap = plot_cfg['colormap_first'](
                np.linspace(0, 1, len(fraction_series))
            )

            for idx, line in enumerate(fraction_series):
                lines += main_axis.plot(
                    unique_revisions,
                    line,
                    linewidth=plot_cfg['linewidth'],
                    color=colormap[idx]
                )

            legend = main_axis.legend(
                handles=lines,
                title=plot_cfg['legend_title'] +
                f" | {base_lib_name} --> {inter_lib_name}",
                # TODO (se-passau/VaRA#545): remove cast with plot config rework
                labels=map(
                    tp.cast(tp.Callable[[int], str], plot_cfg['lable_modif']),
                    degrees
                ),
                loc='upper left',
                prop={
                    'size': plot_cfg['legend_size'],
                    'family': 'monospace'
                }
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

            unique_revisions = data[0][2]

            lib_name_first = data[0][0]
            lib_name_second = data[0][1]
            fraction_series_one = data[0][3]
            degrees_one = degrees[0]

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
                f' - Project {self.plot_kwargs["project"]} | {lib_name_first} '
                f'<--> {lib_name_second}',
                fontsize=8
            )

            lines_first = []
            colormap_first = plot_cfg['colormap_first'](
                np.linspace(0, 1, len(fraction_series_one))
            )
            lines_second = []
            colormap_second = plot_cfg['colormap_second'](
                np.linspace(0.6, 1, len(fraction_series_two))
            )

            for idx, line in enumerate(fraction_series_one):
                lines_first += main_axis.plot(
                    unique_revisions,
                    line,
                    linewidth=plot_cfg['linewidth'],
                    color=colormap_first[idx]
                )

            for idx, line in enumerate(fraction_series_two):
                lines_second += main_axis.plot(
                    unique_revisions,
                    line,
                    linewidth=plot_cfg['linewidth'],
                    color=colormap_second[idx],
                    linestyle="dashdot"
                )

            legend_first = main_axis.legend(
                handles=lines_first,
                title=plot_cfg['legend_title'] +
                f" | {lib_name_first} --> {lib_name_second}",
                # TODO (se-passau/VaRA#545): remove cast with plot config rework
                labels=map(
                    tp.cast(tp.Callable[[int], str], plot_cfg['lable_modif']),
                    degrees_one
                ),
                loc='upper left',
                prop={
                    'size': plot_cfg['legend_size'],
                    'family': 'monospace'
                }
            )
            plt.setp(
                legend_first.get_title(),
                fontsize=plot_cfg['legend_size'],
                family='monospace',
            )
            main_axis.add_artist(legend_first)
            legend_first.set_visible(plot_cfg['legend_visible'])

            legend_second = main_axis.legend(
                handles=lines_second,
                title=plot_cfg['legend_title'] +
                f" | {lib_name_second} --> {lib_name_first}",
                # TODO (se-passau/VaRA#545): remove cast with plot config rework
                labels=map(
                    tp.cast(tp.Callable[[int], str], plot_cfg['lable_modif']),
                    degrees_two
                ),
                loc='upper right',
                prop={
                    'size': plot_cfg['legend_size'],
                    'family': 'monospace'
                }
            )
            plt.setp(
                legend_second.get_title(),
                fontsize=plot_cfg['legend_size'],
                family='monospace'
            )
            main_axis.add_artist(legend_second)
            legend_second.set_visible(plot_cfg['legend_visible'])

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

        # TODO: Save one plot for each plot date
        for idx, mono_data in enumerate(mono_plot_data):
            generate_mono_lib_plot(mono_data, degrees=mono_plot_degrees[idx])

        for idx, multi_data in enumerate(multi_plot_data):
            generate_multi_lib_plot(
                multi_data, degrees=multi_plot_degree_tuples[idx]
            )

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


class BlameInteractionDegreeMultiLib(BlameDegree):
    """Plotting the degree of blame interactions with multiple libraries."""

    NAME = 'b_interaction_degree_multi_lib'

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'legend_title': 'Interaction degrees',
            'fig_title': 'Blame interactions'
        }
        self._multi_lib_degree_plot(view_mode, extra_plot_cfg)

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        return self._calc_missing_revisions(
            DegreeType.interaction, boundary_gradient
        )


class BlameInteractionFractionOverview(BlameDegree):
    """Plotting the degree of blame interactions with multiple libraries."""

    NAME = 'b_interaction_fraction_overview'

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'legend_title': 'Fraction ratio',
            'fig_title': 'Distribution of fractions'
        }
        self._fraction_overview_plot(
            view_mode, DegreeType.interaction, extra_plot_cfg
        )

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
