"""Generate plots for the annotations of the blame verifier."""
import abc
import logging
import typing as tp

import matplotlib.pyplot as plt
import matplotlib.style as style
import numpy as np
import pandas as pd
from matplotlib import cm

from varats.data.databases.blame_verifier_report_database import (
    BlameVerifierReportDatabaseNoOpt,
    BlameVerifierReportDatabaseOpt,
)
from varats.data.reports.commit_report import CommitMap
from varats.plots.cve_annotation import draw_cves
from varats.plots.plot import Plot, PlotDataEmpty
from varats.plots.plot_utils import check_required_args
from varats.plots.repository_churn import draw_code_churn
from varats.utils.project_util import get_project_cls_by_name

LOG = logging.getLogger(__name__)


class BlameVerifierReportPlot(Plot):
    """Base plot for blame verifier plots."""

    @abc.abstractmethod
    def plot(self, view_mode: bool) -> None:
        """Plot the current plot to a file."""

    def _get_verifier_data(self) -> pd.DataFrame:
        commit_map: CommitMap = self.plot_kwargs["get_cmap"]()
        case_study = self.plot_kwargs('plot_case_study', None)
        project_name = self.plot_kwargs['project']
        verifier_plot_df = BlameVerifierReportDatabaseNoOpt.get_data_for_project(
            project_name, ["total", "successes", "failures", "undetermined"],
            commit_map, case_study
        )
        return verifier_plot_df

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        pass


class BlameVerifierReportNoOptPlot(BlameVerifierReportPlot):

    NAME = 'b_verifier_report_no_opt_plot'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        style.use(self.style)
