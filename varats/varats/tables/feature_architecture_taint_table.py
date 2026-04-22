import typing as tp
from collections import namedtuple
from functools import reduce
from itertools import groupby, count
from pyexpat import features
from typing import Any

import click
import pandas as pd
import yaml
from docutils.nodes import entry
from numpy.ma.core import indices

from varats.data.reports.architecture_report import (
    FeatureArchitectureTaintReport,
)
from varats.experiments.vara.feature_architecture_taint_report_experiment import (
    FeatureArchitectureTaintReportExperiment,
)
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.report import ReportFilepath
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.tables.design_structure_matrix import (
    DesignStructureMatrix,
    InternalDSM,
    DependencyTypes,
)
from varats.ts_utils.cli_util import make_cli_option
from varats.ts_utils.click_param_types import REQUIRE_CASE_STUDY


def get_all_regions(
    fat_report: FeatureArchitectureTaintReport
) -> tp.Dict[str, tp.Set[str]]:
    regions_dict = dict()
    for function in fat_report.function_entries.values():
        if function.file_name not in regions_dict:
            regions_dict[function.file_name] = set()
        for region in function.interactions:
            regions_dict[function.file_name].update(region.features)
    return regions_dict


def get_all_regions_tuples(
    fat_report: FeatureArchitectureTaintReport
) -> tp.Tuple[tp.Set[str], tp.Set[str]]:
    a_regions = set()
    features = set()
    for function in fat_report.function_entries.values():
        a_regions.add(function.file_name)
        for region in function.interactions:
            features.update(region.features)
    return a_regions, features


def fat_report_to_table(
    fat_report: FeatureArchitectureTaintReport
) -> pd.DataFrame:
    labels = get_all_regions_tuples(fat_report)
    idx = pd.MultiIndex.from_product(labels, names=["region", "features"])
    df = pd.DataFrame(0, index=idx, columns=idx)
    for function in fat_report.function_entries.values():
        for region in function.interactions:
            for in_region, in_features in region.incommingRegions.items():
                for in_feature in in_features:
                    for feature in region.features:
                        df.loc[(in_region, in_feature),
                               (function.file_name, feature)] += 1
    return df


fat_dependency_attributes = namedtuple(
    'fat_dependency', ['weight', 'incoming_features', 'region_features']
)


def fat_report_to_DSM(
    fat_report: FeatureArchitectureTaintReport
) -> InternalDSM:
    dsm = InternalDSM(
        fat_report.filename.commit_hash.hash, fat_report.filename.project_name
    )
    dependencies: tp.Dict[tp.Tuple[str, str], fat_dependency_attributes] = {}
    for function in fat_report.function_entries.values():
        for region in function.interactions:
            for in_region, in_features in region.incommingRegions.items():
                feature_dict = {
                    k: len(list(v)) for k, v in groupby(sorted(in_features))
                }
                if dependencies.get((in_region, function.file_name)) is None:
                    dependencies[(in_region, function.file_name)
                                ] = fat_dependency_attributes(
                                    len(in_features), feature_dict,
                                    set(region.features)
                                )
                else:
                    existing = dependencies[(in_region, function.file_name)]
                    dependencies[(in_region, function.file_name)
                                ] = fat_dependency_attributes(
                                    existing.weight + len(in_features), {
                                        **existing.incoming_features,
                                        **feature_dict
                                    },
                                    existing.region_features.union(
                                        set(region.features)
                                    )
                                )
    for (src, dst), attributes in dependencies.items():
        if not "root" in attributes.incoming_features != set(
        ) or not "root" in attributes.region_features:
            dsm.add_dependency(src, dst, "Feature Induced")
        dsm.add_dependency(
            src,
            dst,
            "Feature Taint",
            weight=attributes.weight,
            attributes={
                "Incoming Features": attributes.incoming_features,
                "Region Features": attributes.region_features
            }
        )
    return dsm


class FeatureArchitectureTaintTable(Table, table_name="FAT_table"):

    def __init__(
        self, table_config: tp.Any, report_path: ReportFilepath,
        **table_kwargs: tp.Any
    ) -> None:
        super().__init__(table_config, **table_kwargs)
        self.report = FeatureArchitectureTaintReport(report_path.full_path())
        self.revision = report_path.report_filename.commit_hash

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """
        Tabulate the table using the specified format.

        Args:
            table_format: The format to use for tabulation.
            wrap_table: Whether to wrap the table or not.

        Returns:
            The tabulated string representation of the table.
        """
        test = fat_report_to_table(self.report)
        print(test)
        return dataframe_to_table(
            test, table_format, test.style, wrap_table, **{}
        )


class FeatureArchitectureDsm(DesignStructureMatrix, table_name="Fat_DSM"):

    def __init__(
        self,
        table_config: tp.Any,
        report_path: ReportFilepath,
        **table_kwargs: tp.Any,
    ) -> None:
        super().__init__(table_config, **table_kwargs)
        self.report = FeatureArchitectureTaintReport(report_path.full_path())
        self.revision = report_path.report_filename.commit_hash
        self.dsm = fat_report_to_DSM(self.report)
        if "dv8_matrix" in table_kwargs:
            self.dsm.merge(
                InternalDSM.from_dv8_json_string(
                    table_kwargs["dv8_matrix"].read(),
                    table_kwargs["case_study"].project_name
                )
            )
        self.dsm.apply_architecture_model()


def feature_dirven_dependency_filter_factory(
    structural_dependencies: tp.List[str | DependencyTypes] = (
        "Call", "Use", "Extend", "Contain", "Import"
    ),
    threshold: float = 1
) -> tp.Callable[[list[InternalDSM.Dependency]], tp.Optional[str]]:

    def filter_func(
        dependencies: list[InternalDSM.Dependency]
    ) -> tp.Optional[str]:
        dep_dict = {
            k: list(v) for k, v in groupby(
                sorted(dependencies, key=lambda d: d.name), lambda d: d.name
            )
        }
        search = False
        if "Feature Taint" in dep_dict:
            if structural_dependencies:
                for structural_dependency in structural_dependencies:
                    if structural_dependency in dep_dict:
                        search = True
                        break
            if search or structural_dependencies is None:
                feature_interactions = dep_dict["Feature Taint"]
                feature_involvment_count = {}
                for interaction in feature_interactions:
                    for feature, weight in interaction.attributes[
                        "Incoming Features"].items():
                        if feature not in feature_involvment_count:
                            feature_involvment_count[feature] = 0
                        feature_involvment_count[feature] += weight
                root_weight = feature_involvment_count.get("root", 0)
                interesting_feature: tp.Optional[str] = None
                max_weight = 0
                for feature, weight in feature_involvment_count.items():
                    if feature != "root" and weight * threshold >= root_weight and weight > max_weight:
                        interesting_feature = feature
                        max_weight = weight
                return interesting_feature
        return None

    return filter_func


class FeatureInducedDependencyTable(
    Table, table_name="feature_induced_dependency_table"
):

    def __init__(
        self, table_config: tp.Any, report_path: ReportFilepath,
        dv8_matrix: tp.IO, **table_kwargs: tp.Any
    ) -> None:
        super().__init__(table_config, **table_kwargs)
        self.report = FeatureArchitectureTaintReport(report_path.full_path())
        self.revision = report_path.report_filename.commit_hash
        self.dsm = fat_report_to_DSM(self.report)
        self.dsm.merge(
            InternalDSM.from_dv8_json_string(
                dv8_matrix.read(), table_kwargs["case_study"].project_name
            )
        )


#        self.dsm.apply_architecture_model()

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """
        Tabulate the table using the specified format.

        Args:
            table_format: The format to use for tabulation.
            wrap_table: Whether to wrap the table or not.

        Returns:
            The tabulated string representation of the table.
        """
        dsm_dict = self.dsm.as_dsm_dict()
        induced_dependency_filter = feature_dirven_dependency_filter_factory(
            structural_dependencies=[DependencyTypes.IMPORT], threshold=0
        )
        induced_dependencies = {}
        for k in dsm_dict.keys():
            driving_feature = induced_dependency_filter(dsm_dict[k])
            if driving_feature is not None:
                induced_dependencies[k] = driving_feature
        out = "Induced dependencies driven by features:\n"
        for (src, dst), feature in induced_dependencies.items():
            out += f"{src} -> {dst} induced by {feature}\n"
        out += "Likely Drivers:\n"
        driving_dependency_filter = feature_dirven_dependency_filter_factory(
            structural_dependencies=[DependencyTypes.IMPORT], threshold=1
        )
        interesting_dependencies = {}
        for k in dsm_dict.keys():
            driving_feature = driving_dependency_filter(dsm_dict[k])
            if driving_feature is not None:
                interesting_dependencies[k] = driving_feature
        for (src, dst), feature in interesting_dependencies.items():
            out += f"{src} -> {dst} driven by {feature}\n"
        return out


class OverlappingDependencies(
    Table, table_name="overlapping_dependencies_table"
):

    def __init__(
        self, table_config: tp.Any, report_path: ReportFilepath,
        dv8_matrix: tp.IO, **table_kwargs: tp.Any
    ) -> None:
        super().__init__(table_config, **table_kwargs)
        self.report = FeatureArchitectureTaintReport(report_path.full_path())
        self.revision = report_path.report_filename.commit_hash
        json_string = dv8_matrix.read()
        self.dv8_matrix = InternalDSM.from_dv8_json_string(
            json_string, table_kwargs["case_study"].project_name
        )
        self.dsm = fat_report_to_DSM(self.report)
        self.dsm.merge(self.dv8_matrix)


#        self.dsm.apply_architecture_model()

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """
        Tabulate the table using the specified format.

        Args:
            table_format: The format to use for tabulation.
            wrap_table: Whether to wrap the table or not.

        Returns:
            The tabulated string representation of the table.
        """
        dependencies = [dep.name for dep in self.dsm.dependencies]
        df = pd.DataFrame(
            self.dsm.count_overlapping_dependencies(dependencies, dependencies)
        )
        kwargs: tp.Dict[str, tp.Any] = {}
        style = df.style
        if table_format.is_latex():
            kwargs["hrules"] = True
            kwargs["multicol_align"] = "c"
            style.format(precision=2)
        return dataframe_to_table(
            df,
            table_format,
            style,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class ModelInteractions(Table, table_name="model_interactions_table"):

    def __init__(
        self, table_config: tp.Any, report_path: ReportFilepath,
        modules: tp.List[str], **table_kwargs: tp.Any
    ) -> None:
        super().__init__(table_config, **table_kwargs)
        self.report = FeatureArchitectureTaintReport(report_path.full_path())
        self.revision = report_path.report_filename.commit_hash
        self.a = modules[0]
        self.b = modules[1]

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        f_entry = namedtuple("function_entry", ["file_name", "name"])
        region_entry = namedtuple("region_entry", ["in_region", "in_features"])
        filtered_report: dict[Any, Any] = {}

        for function in self.report.function_entries.values():
            if function.file_name.endswith(
                self.a
            ) or function.file_name.endswith(self.b):
                for region in function.interactions:
                    for in_region, in_features in region.incommingRegions.items(
                    ):
                        if in_region.endswith(
                            self.a
                        ) and function.file_name.endswith(
                            self.b
                        ) or in_region.endswith(
                            self.b
                        ) and function.file_name.endswith(self.a):
                            filtered_report[f_entry(
                                function.file_name, function.demangled_name
                            )] = region_entry(in_region, in_features)
        return yaml.dump(filtered_report)


class ScatteringTable(Table, table_name="scattering_table"):

    def __init__(
        self, table_config: tp.Any, report_path: ReportFilepath,
        **table_kwargs: tp.Any
    ):
        super().__init__(table_config, **table_kwargs)
        self.report = FeatureArchitectureTaintReport(report_path.full_path())
        self.revision = report_path.report_filename.commit_hash

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        feature_locations: dict[str, set[str]] = {}
        for function in self.report.function_entries.values():
            for region in function.interactions:
                for feature in region.features:
                    if feature not in feature_locations:
                        feature_locations[feature] = set()
                    feature_locations[feature].add(function.file_name)
        feature_scattering = {
            feature: len(locations)
            for feature, locations in feature_locations.items()
        }
        print("test")
        df = pd.DataFrame.from_dict(
            feature_scattering, orient="index", columns=["Scattering"]
        )
        kwargs: tp.Dict[str, tp.Any] = {}
        style = df.style
        if table_format.is_latex():
            kwargs["hrules"] = True
            kwargs["multicol_align"] = "c"
            style.format(precision=2)
        return dataframe_to_table(
            df,
            table_format,
            style,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class FeatureArchitectureTaintTableGenerator(
    TableGenerator, generator_name="fat-table", options=[REQUIRE_CASE_STUDY]
):
    """Table generator for Feature Architecture Taint Table."""

    def generate(self) -> tp.List[Table]:
        return [
            FeatureArchitectureTaintTable(
                self.table_config, path, **self.table_kwargs
            ) for path in get_processed_revisions_files(
                self.table_kwargs["case_study"].project_name,
                FeatureArchitectureTaintReportExperiment,
                FeatureArchitectureTaintReport,
                file_name_filter=get_case_study_file_name_filter(
                    self.table_kwargs["case_study"]
                ),
                only_newest=True
            )
        ]


class FeatureArchitectureTaintDSMGenerator(
    TableGenerator,
    generator_name="fat-dsm",
    options=[
        REQUIRE_CASE_STUDY,
        make_cli_option(
            "-dv8",
            "--dv8-matrix",
            type=click.File("r"),
            required=False,
            metavar="dv8_matrix",
            help="The dv8 Matrix to convert."
        )
    ]
):
    """Table generator for Feature Architecture Taint Table."""

    def generate(self) -> tp.List[Table]:
        return [
            FeatureArchitectureDsm(
                self.table_config, path, **self.table_kwargs
            ) for path in get_processed_revisions_files(
                self.table_kwargs["case_study"].project_name,
                FeatureArchitectureTaintReportExperiment,
                FeatureArchitectureTaintReport,
                file_name_filter=get_case_study_file_name_filter(
                    self.table_kwargs["case_study"]
                ),
                only_newest=True
            )
        ]


class OverLappingDependenciesTableGenerator(
    TableGenerator,
    generator_name="overlapping-dependencies-table",
    options=[
        REQUIRE_CASE_STUDY,
        make_cli_option(
            "-dv8",
            "--dv8-matrix",
            type=click.File("r"),
            required=True,
            metavar="dv8_matrix",
            help="The dv8 Matrix to convert."
        )
    ]
):
    """Table generator for Feature Induced Dependency Table."""

    def generate(self) -> tp.List[Table]:
        return [
            OverlappingDependencies(
                self.table_config, path, **self.table_kwargs
            ) for path in get_processed_revisions_files(
                self.table_kwargs["case_study"].project_name,
                FeatureArchitectureTaintReportExperiment,
                FeatureArchitectureTaintReport,
                file_name_filter=get_case_study_file_name_filter(
                    self.table_kwargs["case_study"]
                ),
                only_newest=True
            )
        ]


class FeatureInducedDependencyTableGenerator(
    TableGenerator,
    generator_name="feature-induced-dependency-table",
    options=[
        REQUIRE_CASE_STUDY,
        make_cli_option(
            "-dv8",
            "--dv8-matrix",
            type=click.File("r"),
            required=True,
            metavar="dv8_matrix",
            help="The dv8 Matrix to convert."
        )
    ]
):
    """Table generator for Feature Induced Dependency Table."""

    def generate(self) -> tp.List[Table]:
        return [
            FeatureInducedDependencyTable(
                self.table_config, path, **self.table_kwargs
            ) for path in get_processed_revisions_files(
                self.table_kwargs["case_study"].project_name,
                FeatureArchitectureTaintReportExperiment,
                FeatureArchitectureTaintReport,
                file_name_filter=get_case_study_file_name_filter(
                    self.table_kwargs["case_study"]
                ),
                only_newest=True
            )
        ]


class ModuleInteractionsTableGenerator(
    TableGenerator,
    generator_name="module-interactions-table",
    options=[
        REQUIRE_CASE_STUDY,
        make_cli_option(
            "-m",
            "--modules",
            type=str,
            nargs=2,
            required=True,
            metavar="modules",
            help="The dv8 Matrix to convert."
        )
    ]
):

    def generate(self) -> tp.List[Table]:
        return [
            ModelInteractions(self.table_config, path, **self.table_kwargs)
            for path in get_processed_revisions_files(
                self.table_kwargs["case_study"].project_name,
                FeatureArchitectureTaintReportExperiment,
                FeatureArchitectureTaintReport,
                file_name_filter=get_case_study_file_name_filter(
                    self.table_kwargs["case_study"]
                ),
                only_newest=True
            )
        ]


class ScatteringTableGenerator(
    TableGenerator,
    generator_name="scattering-table",
    options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List[Table]:
        return [
            ScatteringTable(self.table_config, path, **self.table_kwargs)
            for path in get_processed_revisions_files(
                self.table_kwargs["case_study"].project_name,
                FeatureArchitectureTaintReportExperiment,
                FeatureArchitectureTaintReport,
                file_name_filter=get_case_study_file_name_filter(
                    self.table_kwargs["case_study"]
                ),
                only_newest=True
            )
        ]
