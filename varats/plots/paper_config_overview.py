"""
Generate graphs that show an overview of the state of all case-studies.
"""

from collections import OrderedDict, defaultdict
from datetime import datetime
from pathlib import Path
import typing as tp

import matplotlib.pyplot as plt
import matplotlib.style as style
import pandas as pd
import numpy as np
import seaborn as sb
from matplotlib.patches import Patch

from varats.data.reports.commit_report import CommitMap
from varats.data.report import MetaReport, FileStatusExtension
from varats.data.reports.empty_report import EmptyReport
from varats.plots.plot import Plot
from varats.plots.plot_utils import check_required_args, find_missing_revisions
import varats.paper.paper_config as PC
from varats.utils.project_util import get_local_project_git


@check_required_args(["cmap", "project"])
def _gen_overview_plot_for_project(**kwargs: tp.Any) -> pd.DataFrame:
    current_config = PC.get_paper_config()

    if 'report_type' in kwargs:
        result_file_type: MetaReport = MetaReport.REPORT_TYPES[
            kwargs['report_type']]
    else:
        result_file_type = EmptyReport
    project = kwargs['project']
    cmap: CommitMap = kwargs['cmap']
    # load data
    revisions_list: tp.List[pd.DataFrame] = []
    for case_study in current_config.get_case_studies(project):
        processed_revisions = case_study.get_revisions_status(result_file_type)

        for rev, status in processed_revisions:
            time_id = cmap.time_id(rev)
            frame = pd.DataFrame(
                {
                    "commit_hash": rev,
                    "commit_id": time_id,
                    "status": status
                },
                index=[0])
            revisions_list.append(frame)
    revisions = pd.concat(revisions_list, ignore_index=True, sort=False)
    return revisions


def _gen_overview_plot(**kwargs: tp.Any) -> tp.Dict[str, tp.Any]:
    """
    Generate the data for the PaperConfigOverviewPlot.
    """
    current_config = PC.get_paper_config()

    if 'report_type' in kwargs:
        result_file_type: MetaReport = MetaReport.REPORT_TYPES[
            kwargs['report_type']]
    else:
        result_file_type = EmptyReport

    projects: tp.Dict[
        str, tp.Dict[int, tp.
                     List[tp.Tuple[str, FileStatusExtension]]]] = OrderedDict()

    for case_study in sorted(current_config.get_all_case_studies(),
                             key=lambda cs: (cs.project_name, cs.version)):
        processed_revisions = case_study.get_revisions_status(result_file_type)

        repo = get_local_project_git(case_study.project_name)
        revisions: tp.Dict[int, tp.List[
            tp.Tuple[str, FileStatusExtension]]] = defaultdict(list)

        # dict: year -> [ (revision: str, status: FileStatusExtension) ]
        for rev, status in processed_revisions:
            commit = repo.get(rev)
            commit_date = datetime.utcfromtimestamp(commit.commit_time)
            revisions[commit_date.year].append((rev, status))

        projects[case_study.project_name] = revisions

    min_years = []
    max_years = []
    for _, revisions in projects.items():
        years = revisions.keys()
        min_years.append(min(years))
        max_years.append(max(years))

    year_range = list(range(min(min_years), max(max_years) + 1))
    project_names = list(projects.keys())

    result: tp.Dict[str, tp.Any] = dict()
    result['year_range'] = year_range
    result['project_names'] = project_names

    revs_successful = []
    revs_blocked = []
    revs_total = []

    for _, revisions in projects.items():
        revs_successful_per_year = []
        revs_blocked_per_year = []
        revs_total_per_year = []
        for year in year_range:
            revs_in_year = revisions[year]
            if not revs_in_year:
                num_revs = np.nan
                num_successful_revs = np.nan
                num_blocked_revs = np.nan
            else:
                num_revs = len(revs_in_year)
                num_successful_revs = len([
                    rev for (rev, status) in revs_in_year
                    if status == FileStatusExtension.Success
                ])
                num_blocked_revs = len([
                    rev for (rev, status) in revs_in_year
                    if status == FileStatusExtension.Blocked
                ])

            revs_successful_per_year.append(num_successful_revs)
            revs_blocked_per_year.append(num_blocked_revs)
            revs_total_per_year.append(num_revs)

        revs_successful.append(revs_successful_per_year)
        revs_blocked.append(revs_blocked_per_year)
        revs_total.append(revs_total_per_year)

    result['revs_successful'] = revs_successful
    result['revs_blocked'] = revs_blocked
    result['revs_total'] = revs_total

    return result


def _plot_overview_graph(results: tp.Dict[str, tp.Any]) -> None:
    """
    Create a plot that shows an overview of all case-studies of a paper-config
    about how many revisions are successful per project/year.

    Args:
        results: the results data as generated by `_gen_overview_plot()`
    """
    num_years = len(results['year_range'])
    num_projects = len(results['project_names'])

    revs_successful = np.asarray(results['revs_successful'])
    revs_blocked = np.asarray(results['revs_blocked'])
    revs_total = np.asarray(results['revs_total'])

    # We want to interpolate three values/colors in the heatmap.
    # As seaborn's heatmap does not allow this, we manually compute the colors
    # for all entries and create a discrete color map from these colors.
    # The entries of the heatmap are then simply the indices of the data
    # mapped to the range [0,1].

    # the +0.5 is needed to prevent floating point precision issues
    revs_success_ratio = np.asarray([
        i + 0.5 if t > 0 else np.nan for i, t in enumerate(revs_total.flatten())
    ])
    revs_success_ratio = revs_success_ratio / len(revs_success_ratio)
    revs_success_ratio = revs_success_ratio.reshape(num_projects, num_years)

    # colors taken from seaborn's default palette
    success_color = np.asarray(
        (0.5568627450980392, 0.7294117647058823, 0.25882352941176473))
    blocked_color = np.asarray(
        (0.20392156862745098, 0.5411764705882353, 0.7411764705882353))
    failed_color = np.asarray((0.8862745098039215, 0.2901960784313726, 0.2))

    def to_color(n_success: float, n_blocked: float,
                 n_total: float) -> np.ndarray:
        f_success = n_success / float(n_total)
        f_blocked = n_blocked / float(n_total)
        f_failed = 1.0 - f_success - f_blocked
        return (f_success * success_color + f_blocked * blocked_color +
                f_failed * failed_color)

    colors = [
        to_color(revs_successful, revs_blocked, revs_total)
        for revs_successful, revs_blocked, revs_total in zip(
            revs_successful.flatten(), revs_blocked.flatten(),
            revs_total.flatten())
    ]

    labels = (np.asarray([
        f"{revs_successful:1.0f}/{revs_blocked:1.0f}\n{revs_total:1.0f}"
        for revs_successful, revs_blocked, revs_total in zip(
            revs_successful.flatten(), revs_blocked.flatten(),
            revs_total.flatten())
    ])).reshape(num_projects, num_years)

    # Note: See the following URL for this size calculation:
    # https://stackoverflow.com/questions/51144934/how-to-increase-the-cell-size-for-annotation-in-seaborn-heatmap

    #TODO (se-passau/VaRA#545): refactor dpi into plot_config. see.
    fontsize_pt = 12
    dpi = 1200

    # compute the matrix height in points and inches
    matrix_height_pt = fontsize_pt * num_projects * 40
    matrix_height_in = matrix_height_pt / dpi

    # compute the required figure height
    top_margin = 0.05
    bottom_margin = 0.10
    figure_height = matrix_height_in / (1 - top_margin - bottom_margin)

    # build the figure instance with the desired height
    plt.subplots(figsize=(18, figure_height),
                 gridspec_kw=dict(top=(1 - top_margin), bottom=bottom_margin))

    ax = sb.heatmap(revs_success_ratio,
                    annot=labels,
                    fmt='',
                    cmap=colors,
                    xticklabels=results['year_range'],
                    yticklabels=results['project_names'],
                    linewidths=.5,
                    vmin=0,
                    vmax=1,
                    cbar=False,
                    square=True)

    legend_entries = [
        Patch(facecolor=success_color),
        Patch(facecolor=blocked_color),
        Patch(facecolor=failed_color),
    ]
    ax.legend(legend_entries,
              ['Success (top left)', 'Blocked (top right)', 'Failed (bottom)'],
              loc='upper left',
              bbox_to_anchor=(1, 1))


class PaperConfigOverviewPlot(Plot):
    """
    Plot showing an overview of all case-studies.
    """

    NAME = 'paper_config_overview_plot'

    def __init__(self, **kwargs: tp.Any) -> None:
        super(PaperConfigOverviewPlot,
              self).__init__("paper_config_overview_plot", **kwargs)

    def plot(self, view_mode: bool) -> None:
        style.use(self.style)
        _plot_overview_graph(_gen_overview_plot(**self.plot_kwargs))

    def show(self) -> None:
        self.plot(True)
        plt.show()

    def save(self, path: tp.Optional[Path] = None,
             filetype: str = 'svg') -> None:
        self.plot(False)

        if path is None:
            plot_dir = Path(self.plot_kwargs["plot_dir"])
        else:
            plot_dir = path

        # TODO (se-passau/VaRA#545): refactor dpi into plot_config. see.
        plt.savefig(plot_dir / ("{graph_name}.{filetype}".format(
            graph_name=self.name, filetype=filetype)),
                    dpi=1200,
                    format=filetype)

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        revisions = _gen_overview_plot_for_project(**self.plot_kwargs)
        revisions.sort_values(by=['commit_id'], inplace=True)
        cmap: CommitMap = self.plot_kwargs['cmap']

        def head_cm_neighbours(lhs_cm: str, rhs_cm: str) -> bool:
            return cmap.time_id(lhs_cm) + 1 == cmap.time_id(rhs_cm)

        def should_insert_revision(last_row: tp.Any,
                                   row: tp.Any) -> tp.Tuple[bool, float]:
            return last_row["status"] != row["status"], 1.0

        def get_commit_hash(row: tp.Any) -> str:
            return str(row["commit_hash"])

        return find_missing_revisions(revisions.iterrows(),
                                      Path(self.plot_kwargs['git_path']), cmap,
                                      should_insert_revision, get_commit_hash,
                                      head_cm_neighbours)
