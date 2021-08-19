"""Generate commit interaction graphs."""

import typing as tp
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import style, cm

from varats.data.databases.commit_interaction_database import (
    CommitInteractionDatabase,
)
from varats.paper.case_study import CaseStudy, CSStage
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plot.plot_utils import check_required_args
from varats.utils.git_util import FullCommitHash


@check_required_args(["project", "get_cmap"])
def _gen_interaction_graph(**kwargs: tp.Any) -> pd.DataFrame:
    """Generate a DataFrame, containing the amount of interactions between
    commits and interactions between the HEAD commit and all others."""
    commit_map = kwargs['get_cmap']()
    case_study = kwargs.get('plot_case_study', None)  # can be None
    project_name = str(kwargs["project"])

    data_frame = CommitInteractionDatabase.get_data_for_project(
        project_name, [
            "revision", "time_id", "CFInteractions", "DFInteractions",
            "HEAD CF Interactions", "HEAD DF Interactions"
        ], commit_map, case_study
    )

    return data_frame


def _plot_interaction_graph(
    data_frame: pd.DataFrame,
    stages: tp.Optional[tp.List[CSStage]] = None,
    view_mode: bool = True
) -> None:
    """Plot a plot, showing the amount of interactions between commits and
    interactions between the HEAD commit and all others."""
    plot_cfg = {
        'linewidth': 2 if view_mode else 1,
        'legend_size': 8 if view_mode else 4,
        'xtick_size': 10 if view_mode else 2
    }

    if stages is None:
        stages = []

    if data_frame.empty:
        raise PlotDataEmpty

    data_frame.sort_values(by=['time_id'], inplace=True)

    # Interaction plot
    axis = plt.subplot(211)  # 211

    plt.setp(axis.get_yticklabels(), fontsize=8, fontfamily='monospace')
    plt.setp(axis.get_xticklabels(), visible=False)

    if stages:
        # We need to plot all different stages separatly
        cf_color_iter = iter(
            reversed(cm.get_cmap('Blues')(np.linspace(0.3, 1, len(stages))))
        )
        df_color_iter = iter(
            reversed(cm.get_cmap('Oranges')(np.linspace(0.3, 1, len(stages))))
        )
        stage_num = len(stages)

        for stage in reversed(stages):
            stage_num -= 1

            cf_mask = np.isfinite(data_frame.CFInteractions.values)
            plt.plot(
                data_frame.revisions.values[cf_mask],
                data_frame.CFInteractions.values[cf_mask],
                color=next(cf_color_iter),
                label="CFInteractions-" + str(stage_num),
                zorder=stage_num + 1,
                linewidth=plot_cfg['linewidth']
            )

            df_mask = np.isfinite(data_frame.DFInteractions.values)
            plt.plot(
                data_frame.revision.values[df_mask],
                data_frame.DFInteractions.values[df_mask],
                color=next(df_color_iter),
                label="DFInteractions-" + str(stage_num),
                zorder=stage_num + 1,
                linewidth=plot_cfg['linewidth']
            )

            def filter_out_stage(data_frame: pd.DataFrame) -> None:

                def cf_removal_helper(
                    row: pd.Series,
                    stage: CSStage = stage
                ) -> tp.Union[np.int64]:
                    if stage.has_revision(row.revision):
                        return np.NaN
                    return row['CFInteractions']

                data_frame['CFInteractions'] = data_frame.apply(
                    cf_removal_helper, axis=1
                )

                def df_removal_helper(
                    row: pd.Series,
                    stage: CSStage = stage
                ) -> tp.Union[np.int64]:
                    if stage.has_revision(row.revision):
                        return np.NaN
                    return row['DFInteractions']

                data_frame['DFInteractions'] = data_frame.apply(
                    func=df_removal_helper, axis=1
                )

            filter_out_stage(data_frame)

    else:
        plt.plot(
            'revision',
            'CFInteractions',
            data=data_frame,
            color='blue',
            linewidth=plot_cfg['linewidth']
        )
        plt.plot(
            'revision',
            'DFInteractions',
            data=data_frame,
            color='red',
            linewidth=plot_cfg['linewidth']
        )

    axis.legend(prop={'size': plot_cfg['legend_size'], 'family': 'monospace'})

    # Head interaction plot
    axis = plt.subplot(212)

    plt.setp(axis.get_yticklabels(), fontsize=8, fontfamily='monospace')
    plt.setp(
        axis.get_xticklabels(),
        fontsize=plot_cfg['xtick_size'],
        fontfamily='monospace',
        rotation=270
    )

    plt.plot(
        'revision',
        'HEAD CF Interactions',
        data=data_frame,
        color='aqua',
        linewidth=plot_cfg['linewidth']
    )
    plt.plot(
        'revision',
        'HEAD DF Interactions',
        data=data_frame,
        color='crimson',
        linewidth=plot_cfg['linewidth']
    )

    plt.xlabel("Revisions", **{'size': '10'})
    axis.legend(prop={'size': plot_cfg['legend_size'], 'family': 'monospace'})


class InteractionPlot(Plot):
    """Plot showing the total amount of commit interactions."""

    NAME = 'interaction_graph'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    @staticmethod
    def supports_stage_separation() -> bool:
        return True

    def plot(self, view_mode: bool) -> None:
        """Plots the current plot."""
        style.use(self.style)

        def cs_filter(data_frame: pd.DataFrame) -> pd.DataFrame:
            """
            Filter out all commit that are not in the case study, if one was
            selected.

            This allows us to only load file related to the case-study.
            """
            if self.plot_kwargs['plot_case_study'] is None:
                return data_frame
            case_study: CaseStudy = self.plot_kwargs['plot_case_study']
            return data_frame[data_frame.apply(
                lambda x: case_study.has_revision(x['head_cm'].split('-')[1]),
                axis=1
            )]

        interaction_plot_df = _gen_interaction_graph(**self.plot_kwargs)

        if self.plot_kwargs['sep_stages']:
            case_study = self.plot_kwargs.get('plot_case_study', None)
        else:
            case_study = None

        _plot_interaction_graph(
            cs_filter(interaction_plot_df),
            case_study.stages if case_study is not None else None, view_mode
        )

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        data_frame = _gen_interaction_graph(**self.plot_kwargs)
        data_frame.sort_values(by=['head_cm'], inplace=True)
        data_frame.reset_index(drop=True, inplace=True)

        def cm_num(head_cm: str) -> int:
            return int(head_cm.split('-')[0])

        def head_cm_neighbours(lhs_cm: str, rhs_cm: str) -> bool:
            return cm_num(lhs_cm) + 1 == cm_num(rhs_cm)

        def rev_calc_helper(data_frame: pd.DataFrame) -> tp.Set[FullCommitHash]:
            new_revs: tp.Set[FullCommitHash] = set()

            df_iter = data_frame.iterrows()
            _, last_row = next(df_iter)
            for _, row in df_iter:
                gradient = abs(1 - (last_row[1] / float(row[1])))
                if gradient > boundary_gradient:
                    lhs_cm = last_row['head_cm']
                    rhs_cm = row['head_cm']

                    if head_cm_neighbours(lhs_cm, rhs_cm):
                        print(
                            "Found steep gradient between neighbours " +
                            "{lhs_cm} - {rhs_cm}: {gradient}".format(
                                lhs_cm=lhs_cm,
                                rhs_cm=rhs_cm,
                                gradient=round(gradient, 5)
                            )
                        )
                        git_path = Path(self.plot_kwargs['git_path'])
                        lhs = lhs_cm.split('-')[1]
                        rhs = rhs_cm.split('-')[1]
                        print(
                            f"Investigate: git -C {git_path} diff {lhs} {rhs}"
                        )
                    else:
                        print(
                            "Unusual gradient between " +
                            "{lhs_cm} - {rhs_cm}: {gradient}".format(
                                lhs_cm=lhs_cm,
                                rhs_cm=rhs_cm,
                                gradient=round(gradient, 5)
                            )
                        )
                        new_rev_id = round(
                            (cm_num(lhs_cm) + cm_num(rhs_cm)) / 2.0
                        )
                        new_rev = self.plot_kwargs['cmap'].c_hash(new_rev_id)
                        print(
                            "-> Adding {rev} as new revision to the sample set".
                            format(rev=new_rev)
                        )
                        new_revs.add(new_rev)
                    print()
                last_row = row
            return new_revs

        print("--- Checking CFInteractions ---")
        missing_revs = rev_calc_helper(
            data_frame[['head_cm', 'CFInteractions']]
        )

        print("--- Checking DFInteractions ---")
        missing_revs.union(
            rev_calc_helper(data_frame[['head_cm', 'DFInteractions']])
        )

        return missing_revs
