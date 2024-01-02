import typing as tp

import pandas as pd
from matplotlib import pyplot as plt
from pylatex import Document, Package

from varats.data.databases.feature_perf_precision_database import (
    Profiler,
    load_accuracy_data,
    VXray,
    PIMTracer,
    EbpfTraceTEF,
    Baseline,
)
from varats.experiments.vara.ma_abelt_experiments import (
    TEFProfileRunnerPrecision,
    EbpfTraceTEFProfileRunnerPrecision,
    PIMProfileRunnerPrecision,
    BlackBoxBaselineRunnerAccuracy,
)
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.tables.feature_perf_precision import cmap_map


class FeaturePerfAccuracyTable(Table, table_name="fperf-accuracy"):

    @staticmethod
    def _prepare_data_table(
        case_studies: tp.List[CaseStudy], profilers: tp.List[Profiler]
    ):
        table_rows = []
        precision_df = load_accuracy_data(case_studies, profilers)

        for cs in case_studies:
            cs_df = precision_df[precision_df["CaseStudy"] == cs.project_name]
            new_row = {
                'CaseStudy':
                    cs.project_name,
                # The number of patch lists is (or should be) the same for all profilers, so we just take
                # then one from the first profiler
                'NumPatchLists':
                    cs_df[(cs_df["Profiler"] == 'Black-box') &
                          (cs_df["Features"] == '__ALL__')].shape[0],
                'NumRegressedFeatures':
                    0
            }

            for profiler in profilers:
                # First, load the accuracy for accumulated times
                prof_df = cs_df[cs_df["Profiler"] == profiler.name]

                new_row[f"{profiler.name}_epsilon_acc"] = prof_df[
                    prof_df["Features"] == "__ALL__"][f"Epsilon"].mean()

                if profiler.name == "Black-box":
                    continue

                new_row[f"{profiler.name}_epsilon_features"] = prof_df[
                    prof_df["Features"] != "__ALL__"]["epsilon"].mean()

                num_regressed_features = prof_df[
                    prof_df["Features"] != "__ALL__"].shape[0]

                new_row[f"NumRegressedFeatures"] = num_regressed_features

            table_rows.append(new_row)

        return pd.DataFrame(table_rows)

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()
        profilers: tp.List[Profiler] = [
            Baseline(experiment=BlackBoxBaselineRunnerAccuracy),
            VXray(experiment=TEFProfileRunnerPrecision),
            PIMTracer(experiment=PIMProfileRunnerPrecision),
            EbpfTraceTEF(experiment=EbpfTraceTEFProfileRunnerPrecision)
        ]

        df = self._prepare_data_table(case_studies, profilers)
        df.sort_values(["CaseStudy"], inplace=True)

        column_names = [
            "CaseStudy", "NumPatchLists", "NumRegressedFeatures",
            "Black-box_epsilon_acc"
        ]

        for p in profilers[1:]:
            column_names.append(f"{p.name}_epsilon_acc")
            column_names.append(f"{p.name}_epsilon_features")

        df = df.reindex(columns=column_names)

        print(f"{df.to_string()}")

        symb_num_regressed_features = "$\\mathbb{F}$"
        symb_num_patches = "$\\mathbb{P}$"
        symb_epsilon_acc = "$\\Epsilon_f$"
        symb_epsilon_feature = "$\\epsilon_f$"

        column_setup = [(' ', "CaseStudy"), ('', symb_num_patches),
                        ('  ', symb_num_regressed_features),
                        ("Black-box", "$\\Epsilon_b$")]

        for p in profilers[1:]:
            column_setup.append((p.name, symb_epsilon_acc))
            column_setup.append((p.name, symb_epsilon_feature))

        df.columns = pd.MultiIndex.from_tuples(column_setup)

        # Table config
        style: pd.io.formats.style.Styler = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["hrules"] = True
            kwargs["convert_css"] = True
            kwargs["column_format"] = "l|rr|r" + ("|rr" * len(profilers[1:]))
            kwargs["multicol_align"] = "c|"
            # pylint: disable=line-too-long
            kwargs[
                "caption"
            ] = f"""Summary of our accuracy measurements separated by subject system. For each subject system we list
            the total number of patch lists across all configurations({symb_num_patches}) and the total
            number of regressed features across all patch lists({symb_num_regressed_features}). For each profiler we report
            mean the accuracies with regards to the total regression measured across the whole execution ({symb_epsilon_acc})
            and the mean of accuracies of regressions measured for each individual feature({symb_epsilon_feature}).
            """
            # pylint: enable=line-too-long
            profiler_subset = [("Black-box", "$\\Epsilon_b$")]
            profiler_subset += [
                (p.name, s)
                for p in profilers[1:]
                for s in [symb_epsilon_acc, symb_epsilon_feature]
            ]

            style.format(precision=2, subset=profiler_subset)

            ryg_map = plt.get_cmap('RdYlGn_r')
            ryg_map = cmap_map(lambda x: x / 1.2 + 0.2, ryg_map)

            style.background_gradient(
                cmap=ryg_map, subset=profiler_subset, vmin=0.0
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


class FeaturePerfAccuracyTableGenerator(
    TableGenerator, generator_name="fperf-accuracy", options=[]
):
    """Generator for 'FeaturePerfAccuracy'."""

    def generate(self) -> tp.List[Table]:
        return [
            FeaturePerfAccuracyTable(self.table_config, **self.table_kwargs)
        ]
