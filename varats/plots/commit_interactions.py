"""
Generate commit interaction graphs.
"""

import typing as tp
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.style as style
from matplotlib import cm
import pandas as pd
import numpy as np

from varats.plots.plot import Plot
from varats.data.cache_helper import (GraphCacheType, build_cached_report_table)
from varats.data.reports.commit_report import CommitReport
from varats.jupyterhelper.file import load_commit_report
from varats.plots.plot_utils import check_required_args
from varats.data.revisions import get_processed_revisions_files
from varats.paper.case_study import (CaseStudy, CSStage,
                                     get_case_study_file_name_filter)


def _build_interaction_table(report_files: tp.List[Path],
                             project_name: str) -> pd.DataFrame:
    """
    Create a table with commit interaction data.

    Returns:
        A pandas data frame with following rows:
            - head_cm
            - CFInteractions
            - DFInteractions
            - HEAD CF Interactions
            - HEAD DF Interactions

    """

    def create_dataframe_layout() -> pd.DataFrame:
        df_layout = pd.DataFrame(columns=[
            'head_cm', 'CFInteractions', 'DFInteractions',
            'HEAD CF Interactions', 'HEAD DF Interactions'
        ])
        df_layout.CFInteractions = df_layout.CFInteractions.astype('int64')
        df_layout.DFInteractions = df_layout.DFInteractions.astype('int64')
        df_layout['HEAD CF Interactions'] = df_layout[
            'HEAD CF Interactions'].astype('int64')
        df_layout['HEAD DF Interactions'] = df_layout[
            'HEAD DF Interactions'].astype('int64')
        return df_layout

    def create_data_frame_for_report(report: CommitReport) -> pd.DataFrame:
        cf_head_interactions_raw = report.number_of_head_cf_interactions()
        df_head_interactions_raw = report.number_of_head_df_interactions()
        return pd.DataFrame(
            {
                'head_cm':
                    report.head_commit,
                'CFInteractions':
                    report.number_of_cf_interactions(),
                'DFInteractions':
                    report.number_of_df_interactions(),
                'HEAD CF Interactions':
                    cf_head_interactions_raw[0] + cf_head_interactions_raw[1],
                'HEAD DF Interactions':
                    df_head_interactions_raw[0] + df_head_interactions_raw[1]
            },
            index=[0])

    return build_cached_report_table(GraphCacheType.CommitInteractionData,
                                     project_name, create_dataframe_layout,
                                     create_data_frame_for_report,
                                     load_commit_report, report_files)


@check_required_args(["project", "get_cmap"])
def _gen_interaction_graph(**kwargs: tp.Any) -> pd.DataFrame:
    """
    Generate a DataFrame, containing the amount of interactions between commits
    and interactions between the HEAD commit and all others.
    """
    commit_map = kwargs['get_cmap']()
    case_study = kwargs.get('plot_case_study', None)  # can be None
    project_name = kwargs["project"]

    report_files = get_processed_revisions_files(
        project_name, CommitReport, get_case_study_file_name_filter(case_study))

    data_frame = _build_interaction_table(report_files, str(project_name))

    data_frame['head_cm'] = data_frame['head_cm'].apply(
        lambda x: "{num}-{head}".format(head=x, num=commit_map.short_time_id(x)
                                       ))

    return data_frame


def _plot_interaction_graph(data_frame: pd.DataFrame,
                            stages: tp.Optional[tp.List[CSStage]] = None,
                            view_mode: bool = True) -> None:
    """
    Plot a plot, showing the amount of interactions between commits and
    interactions between the HEAD commit and all others.
    """
    plot_cfg = {
        'linewidth': 2 if view_mode else 1,
        'legend_size': 8 if view_mode else 4,
        'xtick_size': 10 if view_mode else 2
    }

    if stages is None:
        stages = []

    data_frame['cm_idx'] = data_frame['head_cm'].apply(
        lambda x: int(x.split('-')[0]))
    data_frame.sort_values(by=['cm_idx'], inplace=True)

    # Interaction plot
    axis = plt.subplot(211)  # 211

    for y_label in axis.get_yticklabels():
        y_label.set_fontsize(8)
        y_label.set_fontfamily('monospace')

    for x_label in axis.get_xticklabels():
        x_label.set_visible(False)

    if stages:
        # We need to plot all different stages separatly
        cf_color_iter = iter(
            reversed(cm.get_cmap('Blues')(np.linspace(0.3, 1, len(stages)))))
        df_color_iter = iter(
            reversed(cm.get_cmap('Oranges')(np.linspace(0.3, 1, len(stages)))))
        stage_num = len(stages)

        for stage in reversed(stages):
            stage_num -= 1

            cf_mask = np.isfinite(data_frame.CFInteractions.values)
            plt.plot(data_frame.head_cm.values[cf_mask],
                     data_frame.CFInteractions.values[cf_mask],
                     color=next(cf_color_iter),
                     label="CFInteractions-" + str(stage_num),
                     zorder=stage_num + 1,
                     linewidth=plot_cfg['linewidth'])

            df_mask = np.isfinite(data_frame.DFInteractions.values)
            plt.plot(data_frame.head_cm.values[df_mask],
                     data_frame.DFInteractions.values[df_mask],
                     color=next(df_color_iter),
                     label="DFInteractions-" + str(stage_num),
                     zorder=stage_num + 1,
                     linewidth=plot_cfg['linewidth'])

            def filter_out_stage(data_frame: pd.DataFrame) -> None:

                def cf_removal_helper(row: pd.Series, stage: CSStage = stage
                                     ) -> tp.Union[np.int64]:
                    if stage.has_revision(row['head_cm'].split('-')[1]):
                        return np.NaN
                    return row['CFInteractions']

                data_frame['CFInteractions'] = data_frame.apply(
                    cf_removal_helper, axis=1)

                def df_removal_helper(row: pd.Series, stage: CSStage = stage
                                     ) -> tp.Union[np.int64]:
                    if stage.has_revision(row['head_cm'].split('-')[1]):
                        return np.NaN
                    return row['DFInteractions']

                data_frame['DFInteractions'] = data_frame.apply(
                    func=df_removal_helper, axis=1)

            filter_out_stage(data_frame)

    else:
        plt.plot('head_cm',
                 'CFInteractions',
                 data=data_frame,
                 color='blue',
                 linewidth=plot_cfg['linewidth'])
        plt.plot('head_cm',
                 'DFInteractions',
                 data=data_frame,
                 color='red',
                 linewidth=plot_cfg['linewidth'])

    # plt.ylabel("Interactions", **{'size': '10'})
    axis.legend(prop={'size': plot_cfg['legend_size'], 'family': 'monospace'})

    # Head interaction plot
    axis = plt.subplot(212)

    for y_label in axis.get_yticklabels():
        y_label.set_fontsize(8)
        y_label.set_fontfamily('monospace')

    for x_label in axis.get_xticklabels():
        x_label.set_fontsize(plot_cfg['xtick_size'])
        x_label.set_rotation(270)
        x_label.set_fontfamily('monospace')

    plt.plot('head_cm',
             'HEAD CF Interactions',
             data=data_frame,
             color='aqua',
             linewidth=plot_cfg['linewidth'])
    plt.plot('head_cm',
             'HEAD DF Interactions',
             data=data_frame,
             color='crimson',
             linewidth=plot_cfg['linewidth'])

    plt.xlabel("Revisions", **{'size': '10'})
    # plt.ylabel("HEAD Interactions", **{'size': '10'})
    axis.legend(prop={'size': plot_cfg['legend_size'], 'family': 'monospace'})


class InteractionPlot(Plot):
    """
    Plot showing the total amount of commit interactions.
    """

    NAME = 'interaction_graph'

    def __init__(self, **kwargs: tp.Any) -> None:
        super(InteractionPlot, self).__init__("interaction_graph", **kwargs)

    @staticmethod
    def supports_stage_separation() -> bool:
        return True

    def plot(self, view_mode: bool) -> None:
        style.use(self.style)

        def cs_filter(data_frame: pd.DataFrame) -> pd.DataFrame:
            """
            Filter out all commit that are not in the case study, if one was
            selected. This allows us to only load file related to the
            case-study.
            """
            if self.plot_kwargs['plot_case_study'] is None:
                return data_frame
            case_study: CaseStudy = self.plot_kwargs['plot_case_study']
            return data_frame[data_frame.apply(
                lambda x: case_study.has_revision(x['head_cm'].split('-')[1]),
                axis=1)]

        interaction_plot_df = _gen_interaction_graph(**self.plot_kwargs)

        if self.plot_kwargs['sep_stages']:
            case_study = self.plot_kwargs.get('plot_case_study', None)
        else:
            case_study = None

        _plot_interaction_graph(
            cs_filter(interaction_plot_df),
            case_study.stages if case_study is not None else None, view_mode)

    def show(self) -> None:
        self.plot(True)
        plt.show()

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        data_frame = _gen_interaction_graph(**self.plot_kwargs)
        data_frame.sort_values(by=['head_cm'], inplace=True)
        data_frame.reset_index(drop=True, inplace=True)

        def cm_num(head_cm: str) -> int:
            return int(head_cm.split('-')[0])

        def head_cm_neighbours(lhs_cm: str, rhs_cm: str) -> bool:
            return cm_num(lhs_cm) + 1 == cm_num(rhs_cm)

        def rev_calc_helper(data_frame: pd.DataFrame) -> tp.Set[str]:
            new_revs: tp.Set[str] = set()

            df_iter = data_frame.iterrows()
            _, last_row = next(df_iter)
            for _, row in df_iter:
                gradient = abs(1 - (last_row[1] / float(row[1])))
                if gradient > boundary_gradient:
                    lhs_cm = last_row['head_cm']
                    rhs_cm = row['head_cm']

                    if head_cm_neighbours(lhs_cm, rhs_cm):
                        print("Found steep gradient between neighbours " +
                              "{lhs_cm} - {rhs_cm}: {gradient}".format(
                                  lhs_cm=lhs_cm,
                                  rhs_cm=rhs_cm,
                                  gradient=round(gradient, 5)))
                        print("Investigate: git -C {git_path} diff {lhs} {rhs}".
                              format(git_path=Path(
                                  self.plot_kwargs['git_path']),
                                     lhs=lhs_cm.split('-')[1],
                                     rhs=rhs_cm.split('-')[1]))
                    else:
                        print("Unusual gradient between " +
                              "{lhs_cm} - {rhs_cm}: {gradient}".format(
                                  lhs_cm=lhs_cm,
                                  rhs_cm=rhs_cm,
                                  gradient=round(gradient, 5)))
                        new_rev_id = round(
                            (cm_num(lhs_cm) + cm_num(rhs_cm)) / 2.0)
                        new_rev = self.plot_kwargs['cmap'].c_hash(new_rev_id)
                        print(
                            "-> Adding {rev} as new revision to the sample set".
                            format(rev=new_rev))
                        new_revs.add(new_rev)
                    print()
                last_row = row
            return new_revs

        print("--- Checking CFInteractions ---")
        missing_revs = rev_calc_helper(data_frame[['head_cm',
                                                   'CFInteractions']])

        print("--- Checking DFInteractions ---")
        missing_revs.union(
            rev_calc_helper(data_frame[['head_cm', 'DFInteractions']]))

        return missing_revs
