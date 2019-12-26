"""
Generate plots for the degree of blame interactions.
"""

import typing as tp
import abc
from pathlib import Path
from enum import Enum

import matplotlib.pyplot as plt
from matplotlib import cm
import matplotlib.style as style
import pandas as pd
import numpy as np

from varats.data.cache_helper import build_cached_report_table, GraphCacheType
from varats.jupyterhelper.file import load_blame_report
from varats.plots.plot import Plot, PlotDataEmpty
from varats.data.revisions import get_processed_revisions_files
from varats.data.reports.blame_report import (
    BlameReport, generate_degree_tuples, generate_author_degree_tuples,
    generate_max_time_distribution_tuples,
    generate_avg_time_distribution_tuples)
from varats.plots.plot_utils import check_required_args
from varats.paper.case_study import CaseStudy, get_case_study_file_name_filter
from varats.plots.repository_churn import draw_code_churn

MAX_TIME_BUCKET_SIZE = 42
AVG_TIME_BUCKET_SIZE = 42


class _DegreeType(Enum):
    interaction = "interaction"
    author = "author"
    max_time = "max_time"
    avg_time = "avg_time"


def _build_interaction_table(report_files: tp.List[Path],
                             project_name: str) -> pd.DataFrame:

    def create_dataframe_layout() -> pd.DataFrame:
        df_layout = pd.DataFrame(
            columns=['revision', 'degree_type', 'degree', 'amount', 'fraction'])
        df_layout.degree = df_layout.degree.astype('int64')
        df_layout.amount = df_layout.amount.astype('int64')
        df_layout.fraction = df_layout.fraction.astype('int64')
        return df_layout

    def create_data_frame_for_report(report: BlameReport) -> pd.DataFrame:
        list_of_degree_occurrences = generate_degree_tuples(report)
        degrees, amounts = map(list, zip(*list_of_degree_occurrences))
        total = sum(amounts)

        list_of_author_degree_occurrences = generate_author_degree_tuples(
            report, project_name)
        author_degrees, author_amounts = map(
            list, zip(*list_of_author_degree_occurrences))
        author_total = sum(author_amounts)

        list_of_max_time_deltas = generate_max_time_distribution_tuples(
            report, project_name, MAX_TIME_BUCKET_SIZE)
        max_time_buckets, max_time_amounts = map(list,
                                                 zip(*list_of_max_time_deltas))
        total_max_time_amounts = sum(max_time_amounts)

        list_of_avg_time_deltas = generate_avg_time_distribution_tuples(
            report, project_name, AVG_TIME_BUCKET_SIZE)
        avg_time_buckets, avg_time_amounts = map(list,
                                                 zip(*list_of_avg_time_deltas))
        total_avg_time_amounts = sum(avg_time_amounts)

        amount_of_entries = len(degrees + author_degrees + max_time_buckets +
                                avg_time_buckets)

        return pd.DataFrame(
            {
                'revision': [report.head_commit] * amount_of_entries,
                'degree_type':
                    [_DegreeType.interaction.value] * len(degrees) +
                    [_DegreeType.author.value] * len(author_degrees) +
                    [_DegreeType.max_time.value] * len(max_time_buckets) +
                    [_DegreeType.avg_time.value] * len(avg_time_buckets),
                'degree':
                    degrees + author_degrees + max_time_buckets +
                    avg_time_buckets,
                'amount':
                    amounts + author_amounts + max_time_amounts +
                    avg_time_amounts,
                'fraction':
                    np.concatenate([
                        np.divide(amounts, total),
                        np.divide(author_amounts, author_total),
                        np.divide(max_time_amounts, total_max_time_amounts),
                        np.divide(avg_time_amounts, total_avg_time_amounts)
                    ]),
            },
            index=range(0, amount_of_entries))

    return build_cached_report_table(GraphCacheType.BlameInteractionDegreeData,
                                     project_name, create_dataframe_layout,
                                     create_data_frame_for_report,
                                     load_blame_report, report_files)


@check_required_args(["project", 'get_cmap'])
def _gen_blame_interaction_data(**kwargs: tp.Any) -> pd.DataFrame:
    commit_map = kwargs['get_cmap']()
    case_study = kwargs.get('plot_case_study', None)  # can be None
    project_name = kwargs["project"]

    report_files = get_processed_revisions_files(
        project_name, BlameReport, get_case_study_file_name_filter(case_study))

    data_frame = _build_interaction_table(report_files, str(project_name))

    data_frame['revision'] = data_frame['revision'].apply(
        lambda x: "{num}-{head}".format(head=x, num=commit_map.short_time_id(x)
                                       ))

    return data_frame


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
                     degree_type: _DegreeType,
                     extra_plot_cfg: tp.Optional[tp.Dict[str, tp.Any]] = None,
                     with_churn: bool = True) -> None:
        plot_cfg = {
            'linewidth': 1 if view_mode else 0.25,
            'legend_size': 8 if view_mode else 2,
            'xtick_size': 10 if view_mode else 2,
            'lable_modif': lambda x: x,
            'legend_title': 'MISSING legend_title',
            'fig_title': 'MISSING figure title',
        }
        if extra_plot_cfg is not None:
            plot_cfg.update(extra_plot_cfg)

        style.use(self.style)

        # TODO (se-passau/VaRA#550): refactor cs_filter into helper function
        def cs_filter(data_frame: pd.DataFrame) -> pd.DataFrame:
            """
            Filter out all commits that are not in the case study, if one was
            selected. This allows us to only load files related to the
            case-study.
            """
            if self.plot_kwargs['plot_case_study'] is None or data_frame.empty:
                return data_frame
            case_study: CaseStudy = self.plot_kwargs['plot_case_study']
            return data_frame[data_frame.apply(
                lambda x: case_study.has_revision(x['revision'].split('-')[1]),
                axis=1)]

        interaction_plot_df = _gen_blame_interaction_data(**self.plot_kwargs)
        interaction_plot_df = cs_filter(interaction_plot_df)

        if interaction_plot_df.empty or len(
                np.unique(interaction_plot_df['revision'])) == 1:
            # Plot can only be build with more than one data point
            raise PlotDataEmpty

        # Reduce data frame to rows that match the degree type
        interaction_plot_df = interaction_plot_df[
            interaction_plot_df.degree_type == degree_type.value]

        degree_levels = sorted(np.unique(interaction_plot_df['degree']))

        interaction_plot_df = interaction_plot_df.set_index(
            ['revision', 'degree'])
        interaction_plot_df = interaction_plot_df.reindex(
            pd.MultiIndex.from_product(interaction_plot_df.index.levels,
                                       names=interaction_plot_df.index.names),
            fill_value=0).reset_index()

        interaction_plot_df['cm_idx'] = interaction_plot_df['revision'].apply(
            lambda x: int(x.split('-')[0]))
        interaction_plot_df.cm_idx.astype(int)
        interaction_plot_df.sort_values(by=['cm_idx'], inplace=True)

        sub_df_list = [
            interaction_plot_df.loc[interaction_plot_df['degree'] == x]
            ['fraction'] for x in degree_levels
        ]

        color_map = cm.get_cmap('gist_stern')

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
        uniq_revisions = sorted(np.unique(interaction_plot_df['revision']),
                                key=lambda x: int(x.split('-')[0]))
        main_axis.stackplot(
            uniq_revisions,
            sub_df_list,
            edgecolor='black',
            colors=reversed(
                color_map(
                    np.linspace(0, 1,
                                len(np.unique(
                                    interaction_plot_df['degree']))))),
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

        # draw churn subplot
        if with_churn:
            # for rev in uniq_revisions[::1]:
            #     main_axis.axvline(rev, color='0.90', linewidth=1)

            revs = [
                x
                for x in map(lambda x: tp.cast(object,
                                               x.split('-')[1]), uniq_revisions)
            ]
            draw_code_churn(churn_axis, self.plot_kwargs['project'],
                            self.plot_kwargs['get_cmap'](),
                            lambda x: x[:10] in revs)
            churn_axis.set_yscale('symlog')

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

    def __init__(self, **kwargs: tp.Any):
        super(BlameInteractionDegree, self).__init__('b_interaction_degree',
                                                     **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'legend_title': 'Interaction degrees',
            'fig_title': 'Blame interactions'
        }
        self._degree_plot(view_mode, _DegreeType.interaction, extra_plot_cfg)

    def show(self) -> None:
        self.plot(True)
        plt.show()

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError


class BlameAuthorDegree(BlameDegree):
    """
    Plotting the degree of authors for all blame interactions.
    """

    def __init__(self, **kwargs: tp.Any):
        super(BlameAuthorDegree, self).__init__('b_author_degree', **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'legend_title': 'Author interaction degrees',
            'fig_title': 'Author blame interactions'
        }
        self._degree_plot(view_mode, _DegreeType.author, extra_plot_cfg)

    def show(self) -> None:
        self.plot(True)
        plt.show()

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError


class BlameMaxTimeDistribution(BlameDegree):
    """
    Plotting the degree of max times differences for all blame interactions.
    """

    def __init__(self, **kwargs: tp.Any):
        super(BlameMaxTimeDistribution, self).__init__('b_maxtime_distribution',
                                                       **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'lable_modif':
                lambda x: "{start}-{end}".format(
                    start=x * AVG_TIME_BUCKET_SIZE,
                    end=((x + 1) * AVG_TIME_BUCKET_SIZE) - 1),
            'legend_title':
                'max CommitTimeDelta',
            'fig_title':
                'Max time distribution'
        }
        self._degree_plot(view_mode, _DegreeType.max_time, extra_plot_cfg)

    def show(self) -> None:
        self.plot(True)
        plt.show()

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError


class BlameAvgTimeDistribution(BlameDegree):
    """
    Plotting the degree of avg times differences for all blame interactions.
    """

    def __init__(self, **kwargs: tp.Any):
        super(BlameAvgTimeDistribution, self).__init__('b_avgtime_distribution',
                                                       **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'lable_modif':
                lambda x: "{start}-{end}".format(
                    start=x * AVG_TIME_BUCKET_SIZE,
                    end=((x + 1) * AVG_TIME_BUCKET_SIZE) - 1),
            'legend_title':
                'avg CommitTimeDelta',
            'fig_title':
                'Average time distribution'
        }
        self._degree_plot(view_mode, _DegreeType.avg_time, extra_plot_cfg)

    def show(self) -> None:
        self.plot(True)
        plt.show()

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError
