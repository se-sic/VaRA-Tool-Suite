"""Generate plots that show a detailed overview of the state of one case-
study."""

import typing as tp

import matplotlib.pyplot as plt
from matplotlib import style
from pandas import DataFrame

from varats.data.databases.file_status_database import FileStatusDatabase
from varats.data.reports.empty_report import EmptyReport
from varats.mapping.commit_map import CommitMap, get_commit_map
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot
from varats.plot.plot_utils import find_missing_revisions
from varats.plot.plots import PlotGenerator
from varats.project.project_util import (
    get_project_cls_by_name,
    get_local_project_git_path,
)
from varats.report.report import FileStatusExtension, BaseReport
from varats.ts_utils.cli_util import CLIOptionTy, make_cli_option
from varats.ts_utils.click_param_types import (
    REQUIRE_REPORT_TYPE,
    REQUIRE_CASE_STUDY,
)
from varats.utils.git_util import ShortCommitHash, FullCommitHash

SUCCESS_COLOR = (0.5568627450980392, 0.7294117647058823, 0.25882352941176473)
BLOCKED_COLOR = (0.20392156862745098, 0.5411764705882353, 0.7411764705882353)
FAILED_COLOR = (0.8862745098039215, 0.2901960784313726, 0.2)
COMPILE_ERROR_COLOR = (0.8862745098039215, 0.2901960784313726, 0.2)
MISSING_COLOR = (0.984313725490196, 0.7568627450980392, 0.3686274509803922)
BACKGROUND_COLOR = (0.4666666666666667, 0.4666666666666667, 0.4666666666666667)

OPTIONAL_SHOW_BLOCKED: CLIOptionTy = make_cli_option(
    "--show-blocked/--hide-blocked",
    type=bool,
    default=True,
    required=False,
    metavar="show_blocked",
    help="Shows/hides blocked revisions."
)

OPTIONAL_SHOW_ALL_BLOCKED: CLIOptionTy = make_cli_option(
    "--show-all-blocked/--hide-all-blocked",
    type=bool,
    default=False,
    required=False,
    metavar="show_all_blocked",
    help="Shows/hides all blocked revisions."
)


def _gen_overview_data(tag_blocked: bool,
                       **kwargs: tp.Any) -> tp.Dict[str, tp.List[int]]:
    case_study: CaseStudy = kwargs["case_study"]
    project_name = case_study.project_name
    commit_map: CommitMap = get_commit_map(project_name)
    project = get_project_cls_by_name(project_name)

    if 'report_type' in kwargs:
        result_file_type: tp.Type[BaseReport] = kwargs['report_type']
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


class CaseStudyOverviewPlot(Plot, plot_name="case_study_overview_plot"):
    """Plot showing an overview of all revisions within a case study."""

    NAME = 'case_study_overview_plot'

    def plot(self, view_mode: bool) -> None:
        style.use(self.plot_config.style())
        data = _gen_overview_data(
            self.plot_kwargs["show_blocked"], **self.plot_kwargs
        )

        fig_width = 4
        dot_to_inch = 0.01389
        line_width = 0.75

        _, axis = plt.subplots(1, 1, figsize=(fig_width, 1))

        commit_map: CommitMap = get_commit_map(
            self.plot_kwargs["case_study"].project_name
        )
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

        if self.plot_kwargs["show_all_blocked"]:
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

        case_study: CaseStudy = self.plot_kwargs["case_study"]
        project_name: str = case_study.project_name
        commit_map: CommitMap = get_commit_map(project_name)

        def gen_revision_df(**plot_kwargs: tp.Any) -> DataFrame:
            result_file_type: tp.Type[BaseReport] = plot_kwargs.get(
                "report_type", EmptyReport
            )

            # load data
            frame = FileStatusDatabase.get_data_for_project(
                project_name, ["revision", "time_id", "file_status"],
                commit_map,
                case_study,
                result_file_type=result_file_type,
                tag_blocked=True
            )
            return frame

        revision_df = gen_revision_df(**self.plot_kwargs)
        revision_df.sort_values(by=['time_id'], inplace=True)

        def head_cm_neighbours(
            lhs_cm: ShortCommitHash, rhs_cm: ShortCommitHash
        ) -> bool:
            return commit_map.short_time_id(
                lhs_cm
            ) + 1 == commit_map.short_time_id(rhs_cm)

        def should_insert_revision(last_row: tp.Any,
                                   row: tp.Any) -> tp.Tuple[bool, float]:
            return last_row["file_status"] != row["file_status"], 1.0

        def get_commit_hash(row: tp.Any) -> ShortCommitHash:
            return ShortCommitHash(str(row["revision"]))

        return find_missing_revisions(
            revision_df.iterrows(), get_local_project_git_path(project_name),
            commit_map, should_insert_revision, get_commit_hash,
            head_cm_neighbours
        )


class CaseStudyOverviewGenerator(
    PlotGenerator,
    generator_name="cs-overview-plot",
    options=[
        REQUIRE_REPORT_TYPE, REQUIRE_CASE_STUDY, OPTIONAL_SHOW_BLOCKED,
        OPTIONAL_SHOW_ALL_BLOCKED
    ]
):
    """Generates a case study overview plot."""

    def generate(self) -> tp.List[Plot]:
        return [CaseStudyOverviewPlot(self.plot_config, **self.plot_kwargs)]
