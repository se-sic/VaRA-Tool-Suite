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
        try:
            missing_reports.append(load_commit_report(file_path))
        except KeyError:
            print("KeyError: ", file_path)
        except StopIteration:
            print("YAML file was incomplete: ", file_path)

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


@check_required_args(["result_folder", "project", "get_cmap"])
def _gen_interaction_graph(**kwargs) -> pd.DataFrame:
    """
    Generate a DataFrame, containing the amount of interactions between commits
    and interactions between the HEAD commit and all others.
    """
    commit_map = kwargs['get_cmap']()
    case_study = kwargs.get('plot_case_study', None)  # can be None

    result_dir = Path(kwargs["result_folder"])
    project_name = kwargs["project"]

    reports = []
    for file_path in result_dir.iterdir():
        if file_path.stem.startswith(str(project_name) + "-"):
            if case_study is not None:
                match = CommitReport.FILE_NAME_REGEX.search(
                    Path(file_path).name)
                if match and case_study.has_revision(
                        match.group("file_commit_hash")):
                    reports.append(file_path)
            else:
                reports.append(file_path)

    data_frame = _build_interaction_table(reports, commit_map,
                                          str(project_name))

    data_frame['head_cm'] = data_frame['head_cm'].apply(
        lambda x: "{num}-{head}".format(head=x,
                                        num=commit_map.short_time_id(x)))

    return data_frame


def _plot_interaction_graph(data_frame):
    """
    Plot a plot, showing the amount of interactions between commits and
    interactions between the HEAD commit and all others.
    """
    data_frame.sort_values(by=['head_cm'], inplace=True)

    # Interaction plot
    axis = plt.subplot(211)

    for y_label in axis.get_yticklabels():
        y_label.set_fontsize(8)
        y_label.set_fontfamily('monospace')

    for x_label in axis.get_xticklabels():
        x_label.set_visible(False)

    plt.plot('head_cm', 'CFInteractions', data=data_frame, color='blue')
    plt.plot('head_cm', 'DFInteractions', data=data_frame, color='red')

    # plt.ylabel("Interactions", **{'size': '10'})
    axis.legend(prop={'size': 4, 'family': 'monospace'})

    # Head interaction plot
    axis = plt.subplot(212)

    for y_label in axis.get_yticklabels():
        y_label.set_fontsize(8)
        y_label.set_fontfamily('monospace')

    for x_label in axis.get_xticklabels():
        x_label.set_fontsize(2)
        x_label.set_rotation(270)
        x_label.set_fontfamily('monospace')

    plt.plot('head_cm', 'HEAD CF Interactions', data=data_frame, color='aqua')
    plt.plot(
        'head_cm', 'HEAD DF Interactions', data=data_frame, color='crimson')

    plt.xlabel("Revisions", **{'size': '10'})
    # plt.ylabel("HEAD Interactions", **{'size': '10'})
    axis.legend(prop={'size': 4, 'family': 'monospace'})


class InteractionPlot(Plot):
    """
    Plot showing the total amount of commit interactions.
    """

    def __init__(self, **kwargs):
        super(InteractionPlot, self).__init__("interaction_graph")
        self.__saved_extra_args = kwargs

    @staticmethod
    def supports_stage_separation() -> bool:
        return False

    def plot(self):
        style.use(self.style)

        def cs_filter(data_frame):
            """
            Filter out all commit that are not in the case study, if one was
            selected.
            """
            if self.__saved_extra_args['plot_case_study'] is None:
                return data_frame
            case_study = self.__saved_extra_args['plot_case_study']
            return data_frame[data_frame.apply(
                lambda x: case_study.has_revision(x['head_cm'].split('-')[1]),
                axis=1)]

        _plot_interaction_graph(
            cs_filter(_gen_interaction_graph(**self.__saved_extra_args)))

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

    def calc_missing_revisions(self, boundary_gradient) -> set():
        data_frame = _gen_interaction_graph(**self.__saved_extra_args)
        data_frame.sort_values(by=['head_cm'], inplace=True)
        data_frame.reset_index(drop=True, inplace=True)

        def cm_num(head_cm) -> int:
            return int(head_cm.split('-')[0])

        def head_cm_neighbours(lhs_cm, rhs_cm) -> bool:
            return cm_num(lhs_cm) + 1 == cm_num(rhs_cm)

        def rev_calc_helper(data_frame):
            new_revs = set()

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
                    else:
                        print("Unusual gradient between " +
                              "{lhs_cm} - {rhs_cm}: {gradient}".format(
                                  lhs_cm=lhs_cm,
                                  rhs_cm=rhs_cm,
                                  gradient=round(gradient, 5)))
                        new_rev_id = round(
                            (cm_num(lhs_cm) + cm_num(rhs_cm)) / 2.0)
                        new_rev = self.__saved_extra_args['cmap'].c_hash(
                            new_rev_id)
                        print(
                            "-> Adding {rev} as new revision to the sample set"
                            .format(rev=new_rev))
                        new_revs.add(new_rev)
                    print()
                last_row = row
            return new_revs

        print("--- Checking CFInteractions ---")
        missing_revs = rev_calc_helper(
            data_frame[['head_cm', 'CFInteractions']])

        print("--- Checking DFInteractions ---")
        missing_revs.union(
            rev_calc_helper(data_frame[['head_cm', 'DFInteractions']]))

        return missing_revs
