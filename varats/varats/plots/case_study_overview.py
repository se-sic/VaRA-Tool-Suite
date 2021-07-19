"""Generate plots that show a detailed overview of the state of one case-
studiy."""

import typing as tp
from distutils.util import strtobool

import matplotlib.pyplot as plt
from matplotlib import style

from varats.data.databases.file_status_database import FileStatusDatabase
from varats.data.reports.empty_report import EmptyReport
from varats.mapping.commit_map import CommitMap
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot
from varats.plot.plot_utils import check_required_args
from varats.project.project_util import get_project_cls_by_name
from varats.report.report import FileStatusExtension, BaseReport
from varats.utils.git_util import ShortCommitHash, FullCommitHash

SUCCESS_COLOR = (0.5568627450980392, 0.7294117647058823, 0.25882352941176473)
BLOCKED_COLOR = (0.20392156862745098, 0.5411764705882353, 0.7411764705882353)
FAILED_COLOR = (0.8862745098039215, 0.2901960784313726, 0.2)
COMPILE_ERROR_COLOR = (0.8862745098039215, 0.2901960784313726, 0.2)
MISSING_COLOR = (0.984313725490196, 0.7568627450980392, 0.3686274509803922)
BACKGROUND_COLOR = (0.4666666666666667, 0.4666666666666667, 0.4666666666666667)


@check_required_args(["plot_case_study", "project", "get_cmap"])
def _gen_overview_data(tag_blocked: bool,
                       **kwargs: tp.Any) -> tp.Dict[str, tp.List[int]]:
    case_study: CaseStudy = kwargs["plot_case_study"]
    project_name = kwargs["project"]
    commit_map: CommitMap = kwargs["get_cmap"]()
    project = get_project_cls_by_name(project_name)

    if 'report_type' in kwargs:
        result_file_type: tp.Type[BaseReport] = BaseReport.REPORT_TYPES[
            kwargs['report_type']]
    else:
        result_file_type = EmptyReport

    positions: tp.Dict[str, tp.List[int]] = {
        "background": [],
        "blocked": [],
        "blocked_all": [],
        "compile_error": [],
        "failed": [],
        "missing": [],
        "success": []
    }

    for c_hash, index in commit_map.mapping_items():
        if not case_study.has_revision(ShortCommitHash(c_hash)):
            positions["background"].append(index)
            if hasattr(project, "is_blocked_revision"
                      ) and project.is_blocked_revision(c_hash)[0]:
                positions["blocked_all"].append(index)

    revisions = FileStatusDatabase.get_data_for_project(
        project_name, ["revision", "time_id", "file_status"],
        commit_map,
        case_study,
        result_file_type=result_file_type,
        tag_blocked=tag_blocked
    )
    positions["success"] = (
        revisions[revisions["file_status"] ==
                  FileStatusExtension.SUCCESS.get_status_extension()]
    )["time_id"].tolist()
    positions["failed"] = (
        revisions[revisions["file_status"] ==
                  FileStatusExtension.FAILED.get_status_extension()]
    )["time_id"].tolist()
    positions["blocked"] = (
        revisions[revisions["file_status"] ==
                  FileStatusExtension.BLOCKED.get_status_extension()]
    )["time_id"].tolist()
    positions["blocked_all"].extend((
        revisions[revisions["file_status"] ==
                  FileStatusExtension.BLOCKED.get_status_extension()]
    )["time_id"].tolist())
    positions["missing"] = (
        revisions[revisions["file_status"] ==
                  FileStatusExtension.MISSING.get_status_extension()]
    )["time_id"].tolist()
    positions["compile_error"] = (
        revisions[revisions["file_status"] ==
                  FileStatusExtension.COMPILE_ERROR.get_status_extension()]
    )["time_id"].tolist()

    return positions


class PaperConfigOverviewPlot(Plot):
    """Plot showing an overview of all case-studies."""

    NAME = 'case_study_overview_plot'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        style.use(self.style)

        commit_map: CommitMap = self.plot_kwargs["get_cmap"]()
        show_blocked: bool = strtobool(
            self.plot_kwargs.get("show_blocked", "True")
        )
        show_all_blocked: bool = strtobool(
            self.plot_kwargs.get("show_all_blocked", "False")
        )

        data = _gen_overview_data(show_blocked, **self.plot_kwargs)

        fig_width = 4
        dot_to_inch = 0.01389
        line_width = 0.75

        _, axis = plt.subplots(1, 1, figsize=(fig_width, 1))

        linewidth = (
            fig_width / len(commit_map.mapping_items())
        ) / dot_to_inch * line_width

        axis.eventplot(
            data["background"], linewidths=linewidth, colors=BACKGROUND_COLOR
        )
        axis.eventplot(
            data["success"], linewidths=linewidth, colors=SUCCESS_COLOR
        )
        axis.eventplot(
            data["failed"], linewidths=linewidth, colors=FAILED_COLOR
        )
        axis.eventplot(
            data["missing"], linewidths=linewidth, colors=MISSING_COLOR
        )
        axis.eventplot(
            data["compile_error"],
            linewidths=linewidth,
            colors=COMPILE_ERROR_COLOR
        )

        if show_all_blocked:
            axis.eventplot(
                data["blocked_all"], linewidths=linewidth, colors=BLOCKED_COLOR
            )
        else:
            axis.eventplot(
                data["blocked"], linewidths=linewidth, colors=BLOCKED_COLOR
            )

        axis.set_axis_off()

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError
