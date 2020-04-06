"""
Generate plots for the degree of blame interactions.
"""
import abc
import logging
import typing as tp

import matplotlib.pyplot as plt
import matplotlib.style as style
import pandas as pd
import numpy as np
from matplotlib import cm

from varats.data.databases.blame_interaction_degree_database import (
    DegreeType, BlameInteractionDegreeDatabase)
from varats.data.reports.commit_report import CommitMap
from varats.plots.cve_annotation import draw_cves
from varats.plots.plot import Plot, PlotDataEmpty
from varats.plots.repository_churn import draw_code_churn
from varats.utils.project_util import get_project_cls_by_name

LOG = logging.getLogger(__name__)


def _filter_data_frame(
        degree_type: DegreeType, interaction_plot_df: pd.DataFrame,
        commit_map: CommitMap) -> tp.Tuple[tp.List[str], tp.List[pd.Series]]:
    """
    Reduce data frame to rows that match the degree type
    """
    interaction_plot_df = interaction_plot_df[interaction_plot_df.degree_type ==
                                              degree_type.value]

    degree_levels = sorted(np.unique(interaction_plot_df.degree))
    interaction_plot_df = interaction_plot_df.set_index(['revision', 'degree'])
    interaction_plot_df = interaction_plot_df.reindex(
        pd.MultiIndex.from_product(interaction_plot_df.index.levels,
                                   names=interaction_plot_df.index.names),
        fill_value=0).reset_index()
    # fix missing time_ids introduced by the product index
    interaction_plot_df['time_id'] = interaction_plot_df['revision'].apply(
        commit_map.short_time_id)
    interaction_plot_df.sort_values(by=['time_id'], inplace=True)

    sub_df_list = [
        interaction_plot_df.loc[interaction_plot_df.degree == x].fraction
        for x in degree_levels
    ]
    unique_revisions = sorted(np.unique(interaction_plot_df.revision))

    return unique_revisions, sub_df_list


class BlameDegree(Plot):
    """
    Base plot for blame degree plots.
    """

    @abc.abstractmethod
    def plot(self, view_mode: bool) -> None:
        """Plot the current plot to a file"""

    @abc.abstractmethod
    def show(self) -> None:
        """Show the current plot"""

    def _degree_plot(self,
                     view_mode: bool,
                     degree_type: DegreeType,
                     extra_plot_cfg: tp.Optional[tp.Dict[str, tp.Any]] = None,
                     with_churn: bool = True) -> None:
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
        case_study = self.plot_kwargs.get('plot_case_study',
                                          None)  # can be None
        project_name = self.plot_kwargs["project"]
        interaction_plot_df = BlameInteractionDegreeDatabase.get_data_for_project(
            project_name, [
                "revision", "time_id", "degree_type", "degree", "amount",
                "fraction"
            ], commit_map, case_study)

        if interaction_plot_df.empty or len(
                np.unique(interaction_plot_df['revision'])) == 1:
            # Plot can only be build with more than one data point
            raise PlotDataEmpty

        unique_revisions, sub_df_list = _filter_data_frame(
            degree_type, interaction_plot_df, commit_map)

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
        fig.suptitle(str(plot_cfg['fig_title']) +
                     ' - Project {}'.format(self.plot_kwargs["project"]),
                     fontsize=8)

        main_axis.stackplot(
            unique_revisions,
            sub_df_list,
            edgecolor=plot_cfg['edgecolor'],
            colors=reversed(plot_cfg['color_map'](np.linspace(
                0, 1, len(sub_df_list)))),
            # TODO (se-passau/VaRA#545): remove cast with plot config rework
            labels=map(
                tp.cast(tp.Callable[[str], str], plot_cfg['lable_modif']),
                sorted(np.unique(interaction_plot_df['degree']))),
            linewidth=plot_cfg['linewidth'])

        legend = main_axis.legend(title=plot_cfg['legend_title'],
                                  loc='upper left',
                                  prop={
                                      'size': plot_cfg['legend_size'],
                                      'family': 'monospace'
                                  })
        plt.setp(legend.get_title(),
                 fontsize=plot_cfg['legend_size'],
                 family='monospace')
        legend.set_visible(plot_cfg['legend_visible'])

        # annotate CVEs
        with_cve = self.plot_kwargs.get("with_cve", False)
        if with_cve:
            if "project" not in self.plot_kwargs:
                LOG.error("with_cve is true but no project is given.")
            else:
                project = get_project_cls_by_name(self.plot_kwargs["project"])
                draw_cves(main_axis, project, unique_revisions, plot_cfg)

        # draw churn subplot
        if with_churn:
            draw_code_churn(churn_axis, self.plot_kwargs['project'],
                            self.plot_kwargs['get_cmap'](),
                            lambda x: x[:10] in unique_revisions)

        for y_label in x_axis.get_yticklabels():
            y_label.set_fontsize(8)
            y_label.set_fontfamily('monospace')

        for x_label in x_axis.get_xticklabels():
            x_label.set_fontsize(plot_cfg['xtick_size'])
            x_label.set_rotation(270)
            x_label.set_fontfamily('monospace')


class BlameInteractionDegree(BlameDegree):
    """
    Plotting the degree of blame interactions.
    """

    NAME = 'b_interaction_degree'

    def __init__(self, **kwargs: tp.Any):
        super(BlameInteractionDegree, self).__init__('b_interaction_degree',
                                                     **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'legend_title': 'Interaction degrees',
            'fig_title': 'Blame interactions'
        }
        self._degree_plot(view_mode, DegreeType.interaction, extra_plot_cfg)

    def show(self) -> None:
        self.plot(True)
        plt.show()

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError


class BlameAuthorDegree(BlameDegree):
    """
    Plotting the degree of authors for all blame interactions.
    """

    NAME = 'b_author_degree'

    def __init__(self, **kwargs: tp.Any):
        super(BlameAuthorDegree, self).__init__('b_author_degree', **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'legend_title': 'Author interaction degrees',
            'fig_title': 'Author blame interactions'
        }
        self._degree_plot(view_mode, DegreeType.author, extra_plot_cfg)

    def show(self) -> None:
        self.plot(True)
        plt.show()

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError


class BlameMaxTimeDistribution(BlameDegree):
    """
    Plotting the degree of max times differences for all blame interactions.
    """

    NAME = 'b_maxtime_distribution'

    def __init__(self, **kwargs: tp.Any):
        super(BlameMaxTimeDistribution, self).__init__('b_maxtime_distribution',
                                                       **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'legend_visible': False,
            'fig_title': 'Max time distribution',
            'edgecolor': None,
        }
        self._degree_plot(view_mode, DegreeType.max_time, extra_plot_cfg)

    def show(self) -> None:
        self.plot(True)
        plt.show()

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError


class BlameAvgTimeDistribution(BlameDegree):
    """
    Plotting the degree of avg times differences for all blame interactions.
    """

    NAME = 'b_avgtime_distribution'

    def __init__(self, **kwargs: tp.Any):
        super(BlameAvgTimeDistribution, self).__init__('b_avgtime_distribution',
                                                       **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'legend_visible': False,
            'fig_title': 'Average time distribution',
            'edgecolor': None,
        }
        self._degree_plot(view_mode, DegreeType.avg_time, extra_plot_cfg)

    def show(self) -> None:
        self.plot(True)
        plt.show()

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError
