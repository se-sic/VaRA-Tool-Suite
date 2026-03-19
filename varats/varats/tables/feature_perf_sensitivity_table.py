import re
import typing as tp
from collections import defaultdict

import numpy as np
import pandas as pd
from ijson import IncompleteJSONError
from matplotlib import pyplot as plt
from pylatex import Document, Package

from varats.base.configuration import PatchConfiguration
from varats.data.cache_helper import load_cached_df_or_none, cache_dataframe
from varats.data.databases.feature_perf_precision_database import (
    get_patch_names,
    get_regressing_config_ids_gt,
    compute_profiler_predictions,
    map_to_negative_config_ids,
    map_to_positive_config_ids,
    Profiler,
    Baseline,
    VXray,
    PIMTracer,
    EbpfTraceTEF,
)
from varats.data.metrics import ConfusionMatrix
from varats.data.reports.tef_feature_identifier_report import (
    TEFFeatureIdentifierReport,
)
from varats.experiments.vara.feature_perf_precision import (
    MPRTimeReportAggregate,
)
from varats.experiments.vara.tef_region_identifier import TEFFeatureIdentifier
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config, get_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.provider.patch.patch_provider import PatchProvider
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableGenerator, TableFormat
from varats.tables.feature_perf_precision import cmap_map
from varats.utils.config import load_configuration_map_for_case_study


class FeaturePerfSensitivityTable(Table, table_name="fperf_sensitivity"):
    PROFILERS: tp.List[Profiler] = [
        Baseline(), VXray(), PIMTracer(),
        EbpfTraceTEF()
    ]
    SEVERITIES: tp.List[str] = ["1 ms", "10 ms", "100 ms", "1 s"]

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        print("FEATURE PERF SENSITIVITY TABLE")
        # Data aggregation
        df = pd.DataFrame()
        table_rows = self.__dummy_data()
        dummy_df = pd.concat([df, pd.DataFrame(table_rows)])

        dtypes = {col: dtype for col, dtype in dummy_df.dtypes.items()}

        df = load_cached_df_or_none(
            "fperf_sensitivity_table", "feature_perf_sensitivity", dtypes
        )
        if df is None or True:
            print(
                "No cached data found, computing sensitivity table from scratch."
            )
            df = pd.DataFrame()
            table_rows = self.__by_severity()
            df = pd.concat([df, pd.DataFrame(table_rows)])
            cache_dataframe(
                "fperf_sensitivity_table", "feature_perf_sensitivity", df
            )
        else:
            print("Loaded cached data for sensitivity table.")

        columns_names = ["CaseStudy", "# Regressions"]

        for severity in ["1ms", "10ms", "100ms", "1000ms"]:
            for p in self.PROFILERS:
                columns_names.append(f"{p.name}_{severity}")
        print(f"{df=}")
        df = df.reindex(columns=columns_names)
        print(f"{df=}")
        symb_regressed_configs = "$\\mathbb{R}$"

        column_setup = [(' ', 'CaseStudy'), ('', f'{symb_regressed_configs}')]

        for severity in self.SEVERITIES:
            for p in self.PROFILERS:
                column_setup.append(
                    (severity, f"\\rotatebox{{90}}{{{p.name}}}")
                )

        df.columns = pd.MultiIndex.from_tuples(column_setup)

        print(f"{df=}")

        style: pd.io.formats.style.Styler = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            # LaTeX specific styling
            kwargs["hrules"] = True
            kwargs["convert_css"] = True
            column_format = "clr"
            column_format += "ccccc" * len(self.PROFILERS)
            kwargs["column_format"] = column_format
            kwargs["multicol_align"] = "c"
            kwargs[
                "caption"
            ] = f"""Sensitivity of different profiling approaches with regard to the introduced regression in milliseconds.
        On the left, we show the total amount of regressed program variants that are considered for each regression severity.
        Furthermore, the table depicts for each profiler the relative amount of regressions that were detected.
        """

            # color map
            ryg_map = plt.get_cmap('RdYlGn')
            ryg_map = cmap_map(lambda x: x / 1.2 + 0.2, ryg_map)

            style.background_gradient(
                cmap=ryg_map,
                subset=[(s, f"\\rotatebox{{90}}{{{p.name}}}")
                        for p in self.PROFILERS
                        for s in self.SEVERITIES
                        if p.name != "Base"],
                vmin=0,
                vmax=1.0
            )

            # Conversion for categories and multi-row
            def cs_category_grouping(cs_name: str) -> str:
                if cs_name.startswith("SynthSA"):
                    return "Static Analysis"

                if cs_name.startswith("SynthDA"
                                     ) or cs_name.startswith("SynthOV"):
                    return "Dynamic Analysis"

                if cs_name.startswith("SynthFeature"):
                    return "Configurability"

                if cs_name.startswith("SynthCT"
                                     ) or cs_name.startswith("SynthIP"):
                    return "Implementation Pattern"

                return "Real-World"

            df[('   ', 'Category')
              ] = df[(' ', 'CaseStudy')].apply(cs_category_grouping)

            # Sort by category and case study name, but ensure that "Real-World" is first
            def category_sort_key(cat: str) -> tp.Tuple[int, str]:
                if cat.startswith("Real-"):
                    return (0, cat)
                return (1, cat)

            df.sort_values(
                by=[('   ', 'Category'), (' ', 'CaseStudy')],
                inplace=True,
                key=lambda s: s.map(category_sort_key)
            )

            def add_multirow_column(df: pd.DataFrame) -> pd.DataFrame:
                df.insert(0, ('    ', ' '), "")

                for cat, idx in df.groupby(('   ', 'Category')).groups.items():
                    first_idx = idx[0]
                    label = f"\\tiny{{{cat}}}"
                    label = f"\\rotatebox{{90}}{{{label}}}"
                    df.at[first_idx,
                          ('    ',
                           ' ')] = f"\\multirow{{{len(idx)}}}{{*}}{{{label}}}"

                return df

            df = add_multirow_column(df)
            df.drop(columns=[('   ', 'Category')], inplace=True)

            style.format(
                precision=2,
                subset=[(s, f"\\rotatebox{{90}}{{{p.name}}}")
                        for p in self.PROFILERS
                        for s in self.SEVERITIES]
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

    def __get_affectable_patches(self, project, config_id: int):
        reports = get_processed_revisions_files(
            project.project_name,
            TEFFeatureIdentifier,
            TEFFeatureIdentifierReport,
            get_case_study_file_name_filter(project),
            config_id=config_id
        )

        if len(reports) != 1:
            print(
                f"Expected exactly one TEFFeatureIdentifierReport for project '{project}' and config_id '{config_id}', but found {len(reports)}."
            )
            return []

        id_report = TEFFeatureIdentifierReport(reports[0].full_path())

        patches = id_report.patches_containing_region(["__VARA__DETECT__"])

        for p_name, regions, _ in patches:
            if len(regions) == 1:
                print(
                    f"Detected  __VARA__DETECT__ region without any other region. {project=}/{config_id=}/{p_name=}"
                )

        patch_names = [patch[0].removesuffix("detect") for patch in patches]

        return list(set(patch_names))

    def __get_affectable_patches_manual(
        self, case_study: CaseStudy, config_id: int
    ):
        patch_provider = PatchProvider.get_provider_for_project(
            case_study.project_cls
        )

        patches = patch_provider.get_patches_for_revision(
            case_study.revisions[0].to_short_commit_hash()
        )
        patches = patches["perf_prec"]
        patches = patches.none_of("region_identifier")

        # Identify feature tags for current configuration
        config_map = load_configuration_map_for_case_study(
            get_paper_config(), case_study, PatchConfiguration
        )
        config = config_map.get_configuration(config_id)
        feature_tags = {opt.value for opt in config.options()}

        patches = patches.any_of_features(feature_tags)

        patch_names = [p.shortname.removesuffix("regression") for p in patches]

        # TODO: Remove suffixes from shortnames if necessary

        return list(set(patch_names))

    def __by_severity_alternative(self):
        print("NEW METHOD")
        profilers = self.PROFILERS
        case_studies = get_loaded_paper_config().get_all_case_studies()

        table_rows = []
        num_regressions: tp.Dict[str, int] = {}

        for cs_idx, case_study in enumerate(case_studies):
            print(
                f"Processing cs '{case_study.project_name}' ({cs_idx+1}/{len(case_studies)})"
            )

            rev = case_study.revisions[0]
            project_name = case_study.project_name
            config_ids = case_study.get_config_ids_for_revision(rev)

            regressions_gt: tp.Dict[str, tp.Dict[int, bool]] = {}

            num_regressions[project_name] = sum(
                len(map_to_positive_config_ids(regressions_gt[s]))
                for s in regressions_gt
            )

            # Step 1: Collect GT data from 1000ms patches
            patches = get_patch_names(case_study)

            gt_patches = [p for p in patches if "1000" in p]

            for patch_name in gt_patches:
                patch_id = patch_name.removesuffix("ms").removesuffix("1000")

                patch_gt = get_regressing_config_ids_gt(
                    project_name, case_study, rev, patch_name
                )
                if patch_gt is None:
                    print(
                        f"Could not load GT data for {project_name} and {patch_id}"
                    )
                    continue
                regressions_gt[patch_id] = patch_gt

            # Now that all GT data is loaded, we check the actual detected regressions for each patch
            for patch_name in patches:
                severity_regex = r".*(1|10|100|1000)(ms)?$"

                match = re.search(severity_regex, patch_name)
                if match:
                    patch_severity = int(match.group(1))
                else:
                    print(
                        f"Could not extract severity from patch name '{patch_name}' for project '{case_study.project_name}'"
                    )
                    continue

                patch_id = patch_name.removesuffix("ms").rstrip(
                    "0"
                ).removesuffix("1")

                abs_cut_off = 100
                if patch_severity < 1000:
                    abs_cut_off = 10
                if patch_severity < 100:
                    abs_cut_off = 1
                    rel_cut_off = 0.0
                else:
                    rel_cut_off = 0.01

                for profiler in profilers:
                    new_row: tp.Dict[str, tp.Any] = {
                        "CaseStudy":
                            project_name,
                        "Patch":
                            patch_id,
                        "Severity":
                            patch_severity,
                        "Configs":
                            len(config_ids),
                        "RegressedConfigs":
                            len(regressions_gt[patch_id])
                            if patch_id in regressions_gt else -1
                    }

                    profiler.set_absolute_cut_off(abs_cut_off)
                    profiler.set_relative_cut_off(rel_cut_off)

                    #                    if profiler.name == "Base":
                    #                        profiler.report_type = MPRTimeReportAggregate

                    regressions_actual = compute_profiler_predictions(
                        profiler, project_name, case_study, config_ids,
                        patch_name
                    )

                    if regressions_actual and patch_id in regressions_gt:
                        ground_truth = regressions_gt[patch_id]

                        results = ConfusionMatrix(
                            map_to_positive_config_ids(ground_truth),
                            map_to_negative_config_ids(ground_truth),
                            map_to_positive_config_ids(regressions_actual),
                            map_to_negative_config_ids(regressions_actual)
                        )

                        new_row['precision'] = results.precision()
                        new_row['recall'] = results.recall()
                        new_row['f1_score'] = results.f1_score()
                        new_row['Profiler'] = profiler.name
                        new_row['fp_ids'] = results.getFPs()
                        new_row['fn_ids'] = results.getFNs()
                    else:
                        print(
                            f"Error calculating precision/recall for {project_name=}/{patch_name=}/{profiler.name=}"
                        )
                        new_row['precision'] = np.nan
                        new_row['recall'] = np.nan
                        new_row['f1_score'] = np.nan
                        new_row['Profiler'] = profiler.name
                        new_row['fp_ids'] = []
                        new_row['fn_ids'] = []

                    table_rows.append(new_row)

        raw_df = pd.DataFrame.from_records(table_rows)
        pd.set_option('display.max_columns', None)
        print(f"{raw_df=}")

        table_rows = []
        for cs in case_studies:
            new_row = {
                "CaseStudy": cs.project_name,
                "# Regressions": num_regressions[cs.project_name]
            }
            for severity in [1, 10, 100, 1000]:
                for profiler in profilers:
                    df = raw_df[(raw_df["CaseStudy"] == cs.project_name) &
                                (raw_df["Severity"] == severity) &
                                (raw_df["Profiler"] == profiler.name)]

                    print(f"{df=}")

                    new_row[f"{profiler.name}_{severity}ms"] = df["precision"
                                                                 ].mean()
                    new_row[f"{profiler.name}_{severity}_recall"] = df["recall"
                                                                      ].mean()

            table_rows.append(new_row)

        return table_rows

    def __by_severity(self):
        profilers = self.PROFILERS
        case_studies = get_loaded_paper_config().get_all_case_studies()

        table_rows = []

        for idx1, case_study in enumerate(case_studies):
            print(
                f"Processing case study '{case_study.project_name}' ({idx1+1}/{len(case_studies)})"
            )
            if case_study.project_name != "SynthFeatureInteraction":
                print(f"Skipping case study '{case_study.project_name}'.")
                continue
            rev = case_study.revisions[0]
            project_name = case_study.project_name

            total_num_patches = defaultdict(int)
            regressed_num_regressions = defaultdict(int)

            config_ids = case_study.get_config_ids_for_revision(rev)
            for idx2, config_id in enumerate(config_ids):
                print(
                    f"Processing config '{config_id}' ({idx2+1}/{len(config_ids)})"
                )
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

                patch_names = get_patch_names(case_study)

                affectable_patches = self.__get_affectable_patches(
                    case_study, config_id
                )

                patch_names = [
                    p_name for p_name in patch_names
                    if any([p_name.startswith(p) for p in affectable_patches])
                ]

                for patch_name in patch_names:
                    # TODO: Only consider patches that actually can introduce a regression
                    # TODO: Discuss with Florian: Determine that from the TEFFeatureIdentifierReport or through manual labelling?
                    severity_regex = r".*(1|10|100|1000)(ms)?$"

                    match = re.search(severity_regex, patch_name)
                    if match:
                        patch_severity = int(match.group(1))
                    else:
                        print(
                            f"Could not extract severity from patch name '{patch_name}' for project '{case_study.project_name}' (config_id={config_id})"
                        )
                        continue

                    severity = f"{patch_severity}ms"

                    abs_cut_off = 100
                    if patch_severity < 1000:
                        abs_cut_off = 10
                    if patch_severity < 100:
                        abs_cut_off = 1
                        rel_cut_off = 0.0
                    else:
                        rel_cut_off = 0.01

                    for p in profilers:
                        total_num_patches[f"{p.name}_{severity}"] += 1

                        path = report_paths[p]

                        if not path:
                            continue

                        try:
                            p.set_absolute_cut_off(abs_cut_off)
                            p.set_relative_cut_off(rel_cut_off)
                            if p.is_regression(path, patch_name):
                                regressed_num_regressions[f"{p.name}_{severity}"
                                                         ] += 1
                        except IncompleteJSONError as e:
                            print(
                                f"Error in parsing. Case Study={project_name}, Config_id={config_id}, patch_name={patch_name}, profiler={p.name}"
                            )

            new_row = {'CaseStudy': project_name}

            for k in total_num_patches:
                new_row["# Regressions"] = int(total_num_patches[k])
                new_row[k] = regressed_num_regressions[k] / total_num_patches[k]

            # Option: Show profiler improvements over baseline?
            for p in profilers:
                if p.name == "Base":
                    continue
                for severity in ["1ms", "10ms", "100ms", "1000ms"]:
                    key = f"{p.name}_{severity}"
                    if key not in new_row:
                        continue

                    new_row[key] -= new_row[f"Base_{severity}"]

            table_rows.append(new_row)

        return table_rows

    def __dummy_data(self):
        table_rows = []

        case_studies = [
            cs.project_name
            for cs in get_loaded_paper_config().get_all_case_studies()
        ]

        for cs in case_studies:
            new_row = {'CaseStudy': cs, '# Regressions': 20}
            for p in self.PROFILERS:
                for severity in ["1ms", "10ms", "100ms", "1000ms"]:
                    new_row[f"{p.name}_{severity}"] = 0.5
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
