
import typing as tp

import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
import pandas as pd
import seaborn as sns
from matplotlib import axes

from varats.mapping.commit_map import CommitMap, get_commit_map
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plot.plot_utils import align_yaxis, pad_axes, annotate_correlation
from varats.plot.plots import PlotGenerator
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import FullCommitHash
from varats.data.databases.feature_blame_databases import (
    FeaturesSCFIMetricsDatabase
)
from varats.ts_utils.click_param_types import (
    REQUIRE_CASE_STUDY
)

class FeatureSCFIPlot(Plot, plot_name="feature_scfi_plot"):

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        project_name: str = case_study.project_name
        commit_map: CommitMap = get_commit_map(project_name)

        variables = ["feature", "num_interacting_commits", "feature_scope"]

        df = FeaturesSCFIMetricsDatabase.get_data_for_project(
            project_name, ["revision", "time_id", *variables], commit_map,
            case_study
        )
        
        data = df.sort_values(by=['feature_scope'])
        sns.regplot(data=data, x='feature_scope', y='num_interacting_commits')

class FeatureSCFIPlotGenerator(
    PlotGenerator,
    generator_name="feature-scfi-plot",
    options=[REQUIRE_CASE_STUDY]
):
    """Generates correlation-matrix plot(s) for the selected case study(ies)."""

    def generate(self) -> tp.List[Plot]:
        case_study: CaseStudy = self.plot_kwargs.pop("case_study")
        return [
            FeatureSCFIPlot(
                self.plot_config, case_study=case_study, **self.plot_kwargs
            )
        ]