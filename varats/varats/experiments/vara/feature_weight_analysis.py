"""Module for the FeaturePerfPrecision tables."""
import re
import typing as tp
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
import pandas as pd
#from benchbuild.utils.cmd import git
from matplotlib import colors
from plumbum import local
from pylatex import Document, Package

from varats.data.databases.feature_perf_precision_database import (
    get_patch_names,
    get_regressing_config_ids_gt,
    map_to_positive_config_ids,
    map_to_negative_config_ids,
    Profiler,
    VXray,
    PIMTracer,
    EbpfTraceTEF,
    compute_profiler_predictions,
    load_precision_data,
    load_overhead_data,
)
from varats.data.metrics import ConfusionMatrix
from varats.data.reports.instrumentation_verifier_report import InstrVerifierReport
from varats.experiments.vara.feature_weight import WeightRegionsCountRec
from varats.experiments.vara.feature_weight_default import WeightRegionsCountDef
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import get_local_project_git_path
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.utils.git_util import calc_repo_loc, ChurnConfig

GROUP_SYNTHETIC_CATEGORIES = True

SYNTH_CATEGORIES = [
    "Static Analysis", "Dynamic Analysis", "Configurability",
    "Implementation Pattern"
]

class FeatureWeightAnalysis(Table, table_name="fperf_weight"):
    """Table that compares the different type of weight analysis."""

    @staticmethod
    def _prepare_data_table(
        case_studies: tp.List[CaseStudy]
    ) -> pd.DataFrame:
        df = pd.DataFrame()
        table_rows = []

        for case_study in case_studies:
            reports_rec = get_processed_revisions_files(
                case_study.project_name,
                WeightRegionsCountRec,
                InstrVerifierReport,
                get_case_study_file_name_filter(case_study),
            )

            report_file = reports_rec[0]
            rec_report = InstrVerifierReport(report_file.full_path())

            reports_def = get_processed_revisions_files(
                case_study.project_name,
                WeightRegionsCountDef,
                InstrVerifierReport,
                get_case_study_file_name_filter(case_study),
            )
            report_file = reports_def[0]
            base_report = InstrVerifierReport(report_file.full_path())
            # add the base reports
            row = {
                "Project": case_study.project_name,
                "Base": base_report.num_enters_total(),
                "Recursive": rec_report.num_enters_total(),
            }

            table_rows.append(row)


        return pd.concat([df, pd.DataFrame(table_rows)])

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """Setup performance precision table."""
        case_studies = get_loaded_paper_config().get_all_case_studies()

        # Data aggregation
        df = self._prepare_data_table(case_studies)

        return dataframe_to_table(
            df,
            table_format,
            wrap_table=wrap_table,
            wrap_landscape=True
        )

class FeaturePerfPrecisionTableGenerator(
    TableGenerator, generator_name="fperf-precision", options=[]
):
    """Generator for `FeaturePerfPrecisionTable`."""

    def generate(self) -> tp.List[Table]:
        return [
            FeatureWeightAnalysis(self.table_config, **self.table_kwargs)
        ]
