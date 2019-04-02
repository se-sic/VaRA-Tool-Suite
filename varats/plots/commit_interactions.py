"""
Generate commit interaction graphs.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from varats.data.commit_report import CommitMap
from varats.jupyterhelper.file import load_commit_report
from varats.plots.plot_utils import check_required_args


@check_required_args([
    "result_folder",
    "project",
    "cmap"
])
def gen_interaction_graph(**kwargs):
    commit_map = CommitMap(kwargs["cmap"])
    result_dir = Path(kwargs["result_folder"])
    project_name = kwargs["project"]

    reports = []
    for file_path in result_dir.iterdir():
        if file_path.stem.startswith(str(project_name) +
                                     "-"):
            print("Loading file: ", file_path)
            reports.append(load_commit_report(file_path))

    def sorter(report):
        return commit_map.short_time_id(report.head_commit)

    reports = sorted(reports, key=sorter)

    # Sort with commit map
    commits = []
    cf_interactions = []
    cf_head_interactions = []
    df_interactions = []
    df_head_interactions = []

    for report in reports:
        commits.append(report.head_commit)

        cf_interactions.append(report.number_of_cf_interactions())

        cf_head_interactions_raw = report.number_of_head_cf_interactions()
        cf_head_interactions.append(cf_head_interactions_raw[0] +
                                    cf_head_interactions_raw[1])

        df_interactions.append(report.number_of_df_interactions())

        df_head_interactions_raw = report.number_of_head_df_interactions()
        df_head_interactions.append(df_head_interactions_raw[0] +
                                    df_head_interactions_raw[1])

    data_frame = pd.DataFrame({'x': commits, 'DFInteractions': df_interactions,
                               'CFInteractions': cf_interactions,
                               'HEAD CF Interactions': cf_head_interactions,
                               'HEAD DF Interactions': df_head_interactions})

    # Interaction plot
    axis = plt.subplot(211)

    for y_label in (axis.get_yticklabels()):
        y_label.set_fontsize(14)

    for x_label in (axis.get_xticklabels()):
        x_label.set_visible(False)

    plt.plot('x', 'CFInteractions', data=data_frame, color='blue')
    plt.plot('x', 'DFInteractions', data=data_frame, color='red')

    plt.ylabel("Interactions", **{'size': '14'})

    # Head interaction plot
    axis = plt.subplot(212)

    for y_label in (axis.get_yticklabels()):
        y_label.set_fontsize(14)

    for x_label in (axis.get_xticklabels()):
        x_label.set_fontsize(14)
        x_label.set_rotation(270)

    plt.plot('x', 'HEAD CF Interactions', data=data_frame, color='aqua')
    plt.plot('x', 'HEAD DF Interactions', data=data_frame, color='crimson')

    plt.xlabel("Revisions", **{'size': '14'})
    plt.ylabel("HEAD Interactions", **{'size': '14'})
    plt.show()
