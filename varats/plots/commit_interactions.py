"""
Generate commit interaction graphs.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.style as style
import pandas as pd

from varats.plots.plot import Plot
from varats.data.cache_helper import load_cached_df_or_none, cache_dataframe,\
    GraphCacheType
from varats.data.commit_report import CommitMap, CommitReport
from varats.jupyterhelper.file import load_commit_report
from varats.plots.plot_utils import check_required_args


def _build_interaction_table(report_files: [str], commit_map: CommitMap,
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
    cached_df = load_cached_df_or_none(GraphCacheType.CommitInteractionData,
                                       project_name)
    if cached_df is None:
        cached_df = pd.DataFrame(columns=[
            'head_cm', 'CFInteractions', 'DFInteractions',
            'HEAD CF Interactions', 'HEAD DF Interactions'
        ])

    def report_in_data_frame(report_file, df_col) -> bool:
        match = CommitReport.FILE_NAME_REGEX.search(Path(report_file).name)
        return (match.group("file_commit_hash") == df_col).any()

    missing_report_files = [
        report_file for report_file in report_files
        if not report_in_data_frame(report_file, cached_df['head_cm'])
    ]

    missing_reports = []
    total_missing_reports = len(missing_report_files)
    for num, file_path in enumerate(missing_report_files):
        print(
            "Loading missing file ({num}/{total}): ".format(
                num=(num + 1), total=total_missing_reports), file_path)
        missing_reports.append(load_commit_report(file_path))

    def sorter(report):
        return commit_map.short_time_id(report.head_commit)

    missing_reports = sorted(missing_reports, key=sorter)

    def create_data_frame_for_report(report) -> pd.DataFrame:
        cf_head_interactions_raw = report.number_of_head_cf_interactions()
        df_head_interactions_raw = report.number_of_head_df_interactions()
        return pd.DataFrame({
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

    new_data_frames = [
        create_data_frame_for_report(report) for report in missing_reports
    ]

    new_df = pd.concat(
        [cached_df] + new_data_frames, ignore_index=True, sort=False)

    cache_dataframe(GraphCacheType.CommitInteractionData, project_name, new_df)

    return new_df


@check_required_args(["result_folder", "project", "cmap"])
def _gen_interaction_graph(**kwargs):
    """
    Generate a plot, showing the amount of interactions between commits and
    interactions between the HEAD commit and all others.
    """
    with open(kwargs["cmap"], "r") as c_map_file:
        commit_map = CommitMap(c_map_file.readlines())

    result_dir = Path(kwargs["result_folder"])
    project_name = kwargs["project"]

    reports = []
    for file_path in result_dir.iterdir():
        if file_path.stem.startswith(str(project_name) + "-"):
            reports.append(file_path)

    data_frame = _build_interaction_table(reports, commit_map,
                                          str(project_name))

    # Interaction plot
    axis = plt.subplot(211)

    for y_label in axis.get_yticklabels():
        y_label.set_fontsize(14)

    for x_label in axis.get_xticklabels():
        x_label.set_visible(False)

    plt.plot('head_cm', 'CFInteractions', data=data_frame, color='blue')
    plt.plot('head_cm', 'DFInteractions', data=data_frame, color='red')

    plt.ylabel("Interactions", **{'size': '14'})

    # Head interaction plot
    axis = plt.subplot(212)

    for y_label in axis.get_yticklabels():
        y_label.set_fontsize(14)

    for x_label in axis.get_xticklabels():
        x_label.set_fontsize(14)
        x_label.set_rotation(270)

    plt.plot('head_cm', 'HEAD CF Interactions', data=data_frame, color='aqua')
    plt.plot(
        'head_cm', 'HEAD DF Interactions', data=data_frame, color='crimson')

    plt.xlabel("Revisions", **{'size': '14'})
    plt.ylabel("HEAD Interactions", **{'size': '14'})


class InteractionPlot(Plot):
    """
    Plot showing the total amount of commit interactions.
    """

    def __init__(self, **kwargs):
        super(InteractionPlot, self).__init__("interaction_graph")
        self.__saved_extra_args = kwargs

    def plot(self):
        style.use(self.style)
        _gen_interaction_graph(**self.__saved_extra_args)

    def show(self):
        self.plot()
        plt.show()

    def save(self, filetype='svg'):
        self.plot()

        result_dir = Path(self.__saved_extra_args["result_folder"])
        project_name = self.__saved_extra_args["project"]

        plt.savefig(
            result_dir / (project_name + "_{graph_name}.{filetype}".format(
                graph_name=self.name, filetype=filetype)),
            dpi=1200,
            bbox_inches="tight",
            format=filetype)
