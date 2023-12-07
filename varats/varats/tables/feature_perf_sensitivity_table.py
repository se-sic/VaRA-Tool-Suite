import typing as tp
from collections import defaultdict

import pandas as pd
from ijson import IncompleteJSONError
from matplotlib import pyplot as plt
from pylatex import Document, Package

from varats.data.databases.feature_perf_precision_database import (
    get_patch_names,
    Profiler,
    Baseline,
    VXray,
    PIMTracer,
    EbpfTraceTEF,
)
from varats.experiments.vara.feature_perf_precision import (
    MPRTimeReportAggregate,
)
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableGenerator, TableFormat
from varats.tables.feature_perf_precision import cmap_map


class FeaturePerfSensitivityTable(Table, table_name="fperf_sensitivity"):
    PROFILERS: tp.List[Profiler] = [
        Baseline(), VXray(), PIMTracer(),
        EbpfTraceTEF()
    ]
    SEVERITIES: tp.List[str] = [
        "1 ms", "10 ms", "100 ms", "1000 ms", "10000 ms"
    ]

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        # Data aggregation
        df = pd.DataFrame()
        table_rows = self.__by_severity()
        df = pd.concat([df, pd.DataFrame(table_rows)])

        columns_names = ["CaseStudy", "# Regressions"]

        for p in self.PROFILERS:
            for severity in ["1ms", "10ms", "100ms", "1000ms", "10000ms"]:
                columns_names.append(f"{p.name}_{severity}")
        print(f"{df=}")
        df = df.reindex(columns=columns_names)
        print(f"{df=}")
        symb_regressed_configs = "$\\mathbb{R}$"

        column_setup = [(' ', 'CaseStudy'), ('', f'{symb_regressed_configs}')]

        for p in self.PROFILERS:
            for severity in self.SEVERITIES:
                column_setup.append((p.name, severity))

        df.columns = pd.MultiIndex.from_tuples(column_setup)

        print(f"{df=}")

        style: pd.io.formats.style.Styler = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["hrules"] = True
            kwargs["convert_css"] = True
            column_format = "lr"
            column_format += "ccccc" * len(self.PROFILERS)
            kwargs["column_format"] = column_format
            kwargs["multicol_align"] = "c"
            kwargs[
                "caption"
            ] = f"""Sensitivity of different profiling approaches with regard to the introduced regression in milliseconds.
        On the left, we show the total amount of regressed program variants that are considered for each regression severity.
        Furthermore, the table depicts for each profiler the relative amount of regressions that were detected.
        """
            style.format(precision=2)

            ryg_map = plt.get_cmap('RdYlGn')
            ryg_map = cmap_map(lambda x: x / 1.2 + 0.2, ryg_map)

            style.background_gradient(
                cmap=ryg_map,
                subset=[
                    (p.name, s) for p in self.PROFILERS for s in self.SEVERITIES
                ],
                vmin=0.0,
                vmax=1.0
            )

            style.hide()

        def add_extras(doc: Document) -> None:
            doc.packages.append(Package("amsmath"))
            doc.packages.append(Package("amssymb"))

        return dataframe_to_table(
            df,
            table_format,
            style=style,
            wrap_table=wrap_table,
            wrap_landscape=True,
            document_decorator=add_extras,
            **kwargs
        )

    def __by_severity(self):
        profilers = self.PROFILERS
        case_studies = get_loaded_paper_config().get_all_case_studies()

        table_rows = []

        for case_study in case_studies:
            rev = case_study.revisions[0]
            project_name = case_study.project_name

            total_num_patches = defaultdict(int)
            regressed_num_regressions = defaultdict(int)

            for config_id in case_study.get_config_ids_for_revision(rev):
                report_paths = {}

                # Load reports once in the beginning
                for p in profilers:
                    rep_type = p.report_type if p.name != "Base" else MPRTimeReportAggregate

                    report_files = get_processed_revisions_files(
                        project_name,
                        p.experiment,
                        rep_type,
                        get_case_study_file_name_filter(case_study),
                        config_id=config_id
                    )

                    if len(report_files) != 1:
                        print(
                            f"Found {len(report_files)} report files for profiler {p.name}. Expected 1. (config_id={config_id})"
                        )
                        report_paths[p] = None
                        continue

                    try:
                        report_paths[p] = report_files[0]
                    except Exception as e:
                        print(
                            f"Exception during report parsing for project '{case_study.project_name}' (config_id={config_id}, profiler='{p.name}')"
                        )
                        report_paths[p] = None
                        continue

                patch_names = get_patch_names(case_study, config_id)

                for patch_name in patch_names:
                    if '-' in patch_name and '_' not in patch_name:
                        severity = patch_name.split("-")[-1]
                    else:
                        severity = patch_name.split("_")[-1]

                    for p in profilers:
                        total_num_patches[f"{p.name}_{severity}"] += 1

                        path = report_paths[p]

                        if not path:
                            continue

                        try:
                            if p.is_regression(path, patch_name):
                                regressed_num_regressions[f"{p.name}_{severity}"
                                                         ] += 1
                        except IncompleteJSONError as e:
                            print(
                                f"Error in parsing. Case Study={project_name}, Config_id={config_id}, patch_name={patch_name}, profiler={p.name}"
                            )

            new_row = {'CaseStudy': project_name}

            for k in total_num_patches:
                new_row["# Regressions"] = total_num_patches[k]
                new_row[k] = regressed_num_regressions[k] / total_num_patches[k]

            table_rows.append(new_row)

        return table_rows


class FeaturePerfSensitivityTableGenerator(
    TableGenerator, generator_name="fperf-sensitivity", options=[]
):
    """Generator for FeaturePerfSensitivityTable."""

    def generate(self) -> tp.List['varats.table.table.Table']:
        return [
            FeaturePerfSensitivityTable(self.table_config, **self.table_kwargs)
        ]
