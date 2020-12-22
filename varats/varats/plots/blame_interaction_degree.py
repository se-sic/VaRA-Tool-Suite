"""Generate plots for the degree of blame interactions."""
import abc
import logging
import typing as tp

import matplotlib.pyplot as plt
import matplotlib.style as style
import numpy as np
import pandas as pd
from matplotlib import cm
from plotly import graph_objs as go
from plotly import io as pio
from plumbum import Path

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

    def aggregate_data(df: pd.DataFrame) -> pd.DataFrame:
        aggregated_df = df.groupby(['revision', 'degree']).agg({
            'amount': 'sum',
            'fraction': 'sum'
        })
        return aggregated_df

    if degree_type == DegreeType.interaction:
        interaction_plot_df = aggregate_data(interaction_plot_df)

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


def _get_distinct_base_lib_names(df: pd.DataFrame) -> tp.List[str]:
    return list(np.unique([str(base_lib) for base_lib in df.base_lib]))


def _get_distinct_inter_lib_names(df: pd.DataFrame) -> tp.List[str]:
    return list(np.unique([str(inter_lib) for inter_lib in df.inter_lib]))


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

        interaction_plot_df = interaction_plot_df[(
            interaction_plot_df[['base_lib', 'inter_lib']] == [
                plot_cfg['base_lib'], plot_cfg['inter_lib']
            ]
        ).all(1)]

        def is_lib_combination_existent() -> bool:
            length = len(np.unique(interaction_plot_df['revision']))
            is_empty = interaction_plot_df.empty

            if is_empty or length == 1:
                return False

            return True

        if not is_lib_combination_existent():
            LOG.warning(
                f"There is no interaction from {plot_cfg['base_lib']} to "
                f"{plot_cfg['inter_lib']} or not enough data points."
            )
            raise PlotDataEmpty

        summed_df = interaction_plot_df.groupby(['revision']).sum()

        # Recalculate fractions based on the selected libraries
        for idx, row in interaction_plot_df.iterrows():
            total_amount = summed_df['amount'].loc[row['revision']]
            interaction_plot_df.at[idx,
                                   'fraction'] = row['amount'] / total_amount

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
            f' - Project {self.plot_kwargs["project"]} '
            f'| {plot_cfg["base_lib"]} --> {plot_cfg["inter_lib"]}',
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

        for revision in unique_revisions:
            dataframes_per_revision[revision] = grouped_df.get_group(revision)

        total_amount_per_revision: tp.Dict[str, int] = {}
        base_lib_names_per_revision: tp.Dict[str, tp.List[str]] = {}
        inter_lib_names_per_revision: tp.Dict[str, tp.List[str]] = {}

        for revision in unique_revisions:
            total_amount_per_revision[revision] = dataframes_per_revision[
                revision].sum().amount
            base_lib_names_per_revision[revision
                                       ] = _get_distinct_base_lib_names(
                                           dataframes_per_revision[revision]
                                       )
            inter_lib_names_per_revision[revision
                                        ] = _get_distinct_inter_lib_names(
                                            dataframes_per_revision[revision]
                                        )

        base_lib_fractions: tp.Dict[str, tp.List[float]] = {}
        inter_lib_fractions: tp.Dict[str, tp.List[float]] = {}

        # Calc fractions for base and interacting libraries
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

        base_plot_data: tp.List[tp.List] = [
            base_fraction for base_fraction in base_lib_fractions.values()
        ]

        inter_plot_data: tp.List[tp.List] = [
            inter_fraction for inter_fraction in inter_lib_fractions.values()
        ]

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
            title=plot_cfg['legend_title'] + " | Outgoing interactions",
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
            title=plot_cfg['legend_title'] + " | Ingoing interactions",
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
                project = get_project_cls_by_name(self.plot_kwargs["project"])
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

        plt.setp(x_axis.get_yticklabels(), fontsize=8, fontfamily='monospace')
        plt.setp(
            x_axis.get_xticklabels(),
            fontsize=plot_cfg['xtick_size'],
            fontfamily='monospace',
            rotation=270
        )

    def _library_interactions(
        self,
        view_mode: bool,
        degree_type: DegreeType,
        extra_plot_cfg: tp.Optional[tp.Dict[str, tp.Any]] = None,
    ) -> go.Figure:
        plot_cfg = {
            'fig_title':
                'MISSING figure title',
            'font_size':
                20 if view_mode else 10,
            'width':
                1500,
            'height':
                1000,
            'colormaps': [
                'Greens', 'Reds', 'Blues', 'Greys', 'Oranges', 'Purples',
                'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 'BuPu', 'GnBu',
                'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn'
            ]
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
        highest_degree = df["degree"].max()

        base_lib_names: tp.List[str] = _get_distinct_base_lib_names(df)
        inter_lib_names: tp.List[str] = _get_distinct_inter_lib_names(df)

        # Duplicated lib names are necessary to avoid cycles in the plot
        all_lib_names: tp.List[str] = base_lib_names + inter_lib_names
        all_distinct_lib_names = sorted(set(all_lib_names))
        base_lib_name_index_mapping: tp.Dict[str, int] = {}
        inter_lib_name_index_mapping: tp.Dict[str, int] = {}
        lib_name_to_colormap_mapping: tp.Dict[str, tp.Any] = {}
        lib_name_to_color_shades_mapping: tp.Dict[str, tp.Dict[int, str]] = \
            dict((name, dict()) for name in all_distinct_lib_names)

        sankey_src_idx_list: tp.List[int] = []
        sankey_tgt_idx_list: tp.List[int] = []
        sankey_degree_list: tp.List[int] = []
        sankey_fraction_list: tp.List[float] = []
        sankey_flow_color_list: tp.List[str] = []
        sankey_node_color_list: tp.List[str] = []

        if len(all_distinct_lib_names) > len(plot_cfg['colormaps']):
            LOG.warning(
                "Not enough colormaps for all libraries provided. "
                "Colormaps will be reused."
            )

        for lib_idx, lib_name in \
                enumerate(lib_name_to_color_shades_mapping):

            # If there are not enough colormaps provided, reuse them.
            if len(tp.cast(tp.List, plot_cfg['colormaps'])) <= lib_idx:
                lib_idx = 0

            shades = cm.get_cmap(
                tp.cast(tp.List, plot_cfg['colormaps'])[lib_idx]
            )(np.linspace(0.25, 1, highest_degree + 1))

            lib_name_to_colormap_mapping[lib_name] = cm.get_cmap(
                tp.cast(tp.List, plot_cfg['colormaps'])[lib_idx]
            )
            tmp_color_dict = {}

            for shade_idx, shade in enumerate(shades):
                tmp_color_dict[shade_idx] = str(tuple(shade))

            lib_name_to_color_shades_mapping[lib_name] = tmp_color_dict

        for lib_name in all_lib_names:
            sankey_node_color_list.append(
                f"rgba{tuple(lib_name_to_colormap_mapping[lib_name](0.5))}"
            )

        for idx, name in enumerate(base_lib_names):
            base_lib_name_index_mapping[name] = idx

        idx_offset = len(base_lib_name_index_mapping)

        for idx, name in enumerate(inter_lib_names):
            # Continue the index for the interacting libraries
            inter_lib_name_index_mapping[name] = idx + idx_offset

        for _, row in df.iterrows():
            base_lib = str(row["base_lib"])
            inter_lib = str(row["inter_lib"])
            fraction = float(row["fraction"])
            degree = int(row["degree"])
            color = f"rgba{lib_name_to_color_shades_mapping[base_lib][degree]}"

            sankey_src_idx_list.append(base_lib_name_index_mapping[base_lib])
            sankey_tgt_idx_list.append(inter_lib_name_index_mapping[inter_lib])
            sankey_fraction_list.append(fraction * 100 / len(unique_revisions))
            sankey_degree_list.append(degree)
            sankey_flow_color_list.append(color)

        layout = go.Layout(
            autosize=False, width=plot_cfg['width'], height=plot_cfg['height']
        )
        fig = go.Figure(
            data=[
                go.Sankey(
                    arrangement="perpendicular",
                    node=dict(
                        pad=15,
                        thickness=20,
                        line=dict(color="black", width=0.5),
                        label=all_lib_names,
                        color=sankey_node_color_list,
                        hovertemplate='Fraction ratio = %{'
                        'value}%<extra></extra> '
                    ),
                    link=dict(
                        source=sankey_src_idx_list,
                        target=sankey_tgt_idx_list,
                        value=sankey_fraction_list,
                        color=sankey_flow_color_list,
                        customdata=sankey_degree_list,
                        hovertemplate='Interaction has a fraction ratio of %{'
                        'value}%<br /> and a degree of %{'
                        'customdata}<extra></extra>',
                    )
                )
            ]
        )

        fig.update_layout(
            title_text=plot_cfg['fig_title'], font_size=plot_cfg['font_size']
        )
        if not view_mode:
            fig.layout = layout

        return fig

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
    """
    Plotting the degree of blame interactions between two libraries.

    Pass the selected base library (base_lib) and interacting library
    (inter_lib) as key-value pairs after the plot name. E.g., base_lib=Foo
    inter_lib=Bar
    """

    NAME = 'b_interaction_degree_multi_lib'

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        if 'base_lib' and 'inter_lib' in self.plot_kwargs:
            base_lib = self.plot_kwargs['base_lib']
            inter_lib = self.plot_kwargs['inter_lib']
        else:
            LOG.warning("No library names were provided.")
            raise PlotDataEmpty

        extra_plot_cfg = {
            'legend_title': 'Interaction degrees',
            'fig_title': 'Blame interactions',
            'base_lib': base_lib,
            'inter_lib': inter_lib
        }
        self._multi_lib_degree_plot(
            view_mode, DegreeType.interaction, extra_plot_cfg
        )

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        return self._calc_missing_revisions(
            DegreeType.interaction, boundary_gradient
        )


class BlameInteractionFractionOverview(BlameDegree):
    """Plotting the fraction distribution of in-/outgoing blame interactions
    from all project libraries."""

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


class BlameLibraryInteractions(BlameDegree):
    """Plotting the dependencies of blame interactions from all project
    libraries either as interactive plot in the browser or static image."""

    NAME = 'b_library_interactions'

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)
        self.__figure = go.Figure()

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'fig_title': 'Library interactions',
            'width': 1500,
            'height': 1000
        }
        self.__figure = self._library_interactions(
            view_mode, DegreeType.interaction, extra_plot_cfg
        )

    def show(self) -> None:
        try:
            self.plot(True)
        except PlotDataEmpty:
            LOG.warning(f"No data for project {self.plot_kwargs['project']}.")
            return
        self.__figure.show()

    def save(
        self, path: tp.Optional[Path] = None, filetype: str = 'png'
    ) -> None:
        try:
            self.plot(False)
        except PlotDataEmpty:
            LOG.warning(f"No data for project {self.plot_kwargs['project']}.")
            return

        if path is None:
            plot_dir = Path(self.plot_kwargs["plot_dir"])
        else:
            plot_dir = path

        pio.write_image(
            self.__figure,
            plot_dir + "/" + self.plot_file_name(filetype),
            format=filetype
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
