
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

class FeatureSCFIPlot(Plot, plot_name="feature_scfi_plot"):

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        project_name: str = case_study.project_name
        commit_map: CommitMap = get_commit_map(project_name)

        df = FeaturesSCFIMetricsDatabase.get_data_for_project(
            project_name, ["feature", "num_interacting_commits", "feature_scope"], commit_map,
            case_study
        )
        # nur zum testen, failed schon vorher
        print(df)

class FeatureSCFIPlotGenerator(
    PlotGenerator,
    generator_name="feature-scfi-plot",
    options=[]
):
    """Generates correlation-matrix plot(s) for the selected case study(ies)."""

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            FeatureSCFIPlot(
                self.plot_config, case_study=cs, **self.plot_kwargs
            ) for cs in case_studies
        ]