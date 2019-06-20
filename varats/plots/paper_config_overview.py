"""
Generate graphs that show an overview of the state of all case-studies.
"""

from collections import OrderedDict, defaultdict
from datetime import datetime
from pathlib import Path
import typing as tp

import matplotlib.pyplot as plt
import matplotlib.style as style
import numpy as np
import pygit2
import seaborn as sb

from varats.plots.plot import Plot
from varats.data.commit_report import CommitReport
from varats.plots.plot_utils import check_required_args
import varats.paper.paper_config as PC
from varats.settings import CFG
from varats.utils.project_util import get_local_project_git_path


def _gen_overview_plot():
    """
    Generate the data for the PaperConfigOverviewPlot.
    """
    PC.load_paper_config(
        str(CFG["paper_config"]["folder"]) + "/" +
        str(CFG["paper_config"]["current_config"]))

    current_config = PC.get_paper_config()

    projects = OrderedDict()

    for case_study in sorted(
            current_config.get_all_case_studies(),
            key=lambda cs: (cs.project_name, cs.version)):
        processed_revisions = list(
            dict.fromkeys(case_study.processed_revisions(CommitReport)))

        git_path = get_local_project_git_path(case_study.project_name)
        repo_path = pygit2.discover_repository(str(git_path))
        repo = pygit2.Repository(repo_path)

        revisions = defaultdict(list)

        # dict: year -> [ (revision: str, success: bool) ]
        for rev in case_study.revisions:
            commit = repo.get(rev)
            commit_date = datetime.utcfromtimestamp(commit.commit_time)
            success = rev in processed_revisions
            revisions[commit_date.year].append((rev, success))

        projects[case_study.project_name] = revisions

    min_years = []
    max_years = []
    for _, revisions in projects.items():
        years = revisions.keys()
        min_years.append(min(years))
        max_years.append(max(years))

    year_range = list(range(min(min_years), max(max_years) + 1))
    project_names = list(projects.keys())

    result = dict()
    result['year_range'] = year_range
    result['project_names'] = project_names

    revs_successful = []
    revs_total = []

    for _, revisions in projects.items():
        revs_successful_per_year = []
        revs_total_per_year = []
        for year in year_range:
            revs_in_year = revisions[year]
            if not revs_in_year:
                num_revs = np.nan
                num_successful_revs = np.nan
            else:
                num_revs = len(revs_in_year)
                num_successful_revs = sum(1 for (rev, success) in revs_in_year if success)

            revs_successful_per_year.append(num_successful_revs)
            revs_total_per_year.append(num_revs)

        revs_successful.append(revs_successful_per_year)
        revs_total.append(revs_total_per_year)

    result['revs_successful'] = revs_successful
    result['revs_total'] = revs_total

    return result


def _plot_overview_graph(results) -> None:
    """
    Create a plot that shows an overview of all case-studies of a paper-config
    about how many revisions are successful per project/year.
    """
    revs_successful = np.asarray(results['revs_successful'])
    revs_total = np.asarray(results['revs_total'])
    revs_success_ratio = revs_successful / revs_total

    year_range = results['year_range']
    project_names = results['project_names']

    labels = (np.asarray(["{0:1.0f}/{1:1.0f}".format(revs_successful, revs_total)
                          for revs_successful, revs_total
                          in zip(revs_successful.flatten(), revs_total.flatten())])).reshape(
                              len(project_names), len(year_range))

    sb.heatmap(revs_success_ratio, annot=labels, fmt='', cmap="BrBG",
               xticklabels=year_range, yticklabels=project_names,
               vmin=0, vmax=1,
               cbar_kws={'label': 'success ratio'})


class PaperConfigOverviewPlot(Plot):
    """
    Plot showing an overview of all case-studies.
    """

    @check_required_args(["result_folder"])
    def __init__(self, **kwargs):
        super(PaperConfigOverviewPlot, self).__init__("paper_config_overview_plot")
        self.__saved_extra_args = kwargs

    def plot(self, view_mode):
        style.use(self.style)
        _plot_overview_graph(
            _gen_overview_plot())

    def show(self):
        self.plot(False)
        plt.show()

    def save(self, filetype='svg'):
        self.plot(False)

        result_dir = Path(self.__saved_extra_args["result_folder"])

        plt.savefig(
            result_dir / ("{graph_name}.{filetype}".format(
                graph_name=self.name, filetype=filetype)),
            dpi=1200,
            bbox_inches="tight",
            format=filetype)

    def calc_missing_revisions(self, boundary_gradient) -> tp.Set:
        return set()
