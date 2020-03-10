"""
Generate plots that show a detailed overview of the state of one case-studiy.
"""

import typing as tp

import matplotlib.pyplot as plt
import matplotlib.style as style

from varats.data.report import MetaReport, FileStatusExtension
from varats.data.reports.commit_report import CommitMap
from varats.data.reports.empty_report import EmptyReport
from varats.paper.case_study import CaseStudy
from varats.plots.plot import Plot
from varats.plots.plot_utils import check_required_args
from varats.utils.project_util import get_project_cls_by_name

success_color = (0.5568627450980392, 0.7294117647058823, 0.25882352941176473)
blocked_color = (0.20392156862745098, 0.5411764705882353, 0.7411764705882353)
failed_color = (0.8862745098039215, 0.2901960784313726, 0.2)
compile_error_color = (0.8862745098039215, 0.2901960784313726, 0.2)
missing_color = (0.984313725490196, 0.7568627450980392, 0.3686274509803922)
background_color = (0.4666666666666667, 0.4666666666666667, 0.4666666666666667)


@check_required_args(["plot_case_study", "project", "get_cmap"])
def _gen_overview_data(mark_blocked: bool = True,
                       **kwargs: tp.Any) -> tp.Dict[str, tp.List[int]]:
    case_study: CaseStudy = kwargs.get('plot_case_study')  # can be None
    project_name = kwargs["project"]
    commit_map: CommitMap = kwargs["get_cmap"]()
    project = get_project_cls_by_name(project_name)

    if 'report_type' in kwargs:
        result_file_type: MetaReport = MetaReport.REPORT_TYPES[
            kwargs['report_type']]
    else:
        result_file_type = EmptyReport

    positions = {
        "background": [],
        "blocked": [],
        "blocked_all": [],
        "compile_error": [],
        "failed": [],
        "missing": [],
        "success": []
    }

    for c_hash, index in commit_map.mapping_items():
        if not case_study.has_revision(c_hash):
            positions["background"].append(index)
            if hasattr(project, "is_blocked_revision"
                      ) and project.is_blocked_revision(c_hash)[0]:
                positions["blocked_all"].append(index)

    processed_revisions = case_study.get_revisions_status(
        result_file_type, tag_blocked=mark_blocked)
    for rev, status in processed_revisions:
        index = commit_map.short_time_id(rev)
        if status is FileStatusExtension.Success:
            positions["success"].append(index)
        elif status is FileStatusExtension.Failed:
            positions["failed"].append(index)
        elif status is FileStatusExtension.Blocked:
            positions["blocked"].append(index)
            positions["blocked_all"].append(index)
        elif status is FileStatusExtension.Missing:
            positions["missing"].append(index)
        elif status is FileStatusExtension.CompileError:
            positions["compile_error"].append(index)
        else:
            positions["background"].append(index)

    return positions


class PaperConfigOverviewPlot(Plot):
    """
    Plot showing an overview of all case-studies.
    """

    NAME = 'case_study_overview_plot'

    def __init__(self, **kwargs: tp.Any) -> None:
        super(PaperConfigOverviewPlot,
              self).__init__("paper_config_overview_plot", **kwargs)

    def plot(self, view_mode: bool) -> None:
        style.use(self.style)

        commit_map: CommitMap = self.plot_kwargs["get_cmap"]()

        show_blocked = True
        show_all_blocked = True

        data = _gen_overview_data(show_blocked, **self.plot_kwargs)

        fig_width = 4
        dot_to_inch = 0.01389
        line_width = 0.75

        fig, axis = plt.subplots(1, 1, figsize=(fig_width, 1))

        linewidth = (fig_width /
                     len(commit_map.mapping_items())) / dot_to_inch * line_width

        # axis.eventplot(data["background"],
        #                linewidths=linewidth,
        #                # lineoffsets=0,
        #                colors=background_color)
        axis.eventplot(
            data["success"],
            linewidths=linewidth,
            # lineoffsets=1,
            colors=success_color)
        axis.eventplot(
            data["failed"],
            linewidths=linewidth,
            # lineoffsets=2,
            colors=failed_color)
        axis.eventplot(
            data["missing"],
            linewidths=linewidth,
            # lineoffsets=3,
            colors=missing_color)
        axis.eventplot(
            data["compile_error"],
            linewidths=linewidth,
            # lineoffsets=4,
            colors=compile_error_color)

        if show_all_blocked:
            axis.eventplot(
                data["blocked_all"],
                linewidths=linewidth,
                # lineoffsets=5,
                colors=blocked_color)
        else:
            axis.eventplot(
                data["blocked"],
                linewidths=linewidth,
                # lineoffsets=5,
                colors=blocked_color)

        axis.set_axis_off()

    def show(self) -> None:
        self.plot(True)
        plt.show()

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError
