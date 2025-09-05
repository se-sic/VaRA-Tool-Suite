import typing as tp
from functools import reduce

import pandas as pd
from numpy.ma.core import indices

from varats.data.reports.architecture_report import (
    FeatureArchitectureTaintReport,
)
from varats.experiments.vara.feature_architecture_taint_report_experiment import (
    FeatureArchitectureTaintReportExperiment,
)
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.report import ReportFilepath
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.tables.design_structure_matrix import DesignStructureMatrix, DSM
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


def fat_report_to_DSM(fat_report: FeatureArchitectureTaintReport) -> DSM:
    entries, features = get_all_regions_tuples(fat_report)
    dsm = DSM(
        fat_report.filename.commit_hash.hash, fat_report.filename.project_name
    )
    feature_uid_dict: tp.Dict[str, int] = {}
    region_uid_dict: tp.Dict[str, tp.Tuple[int, int]] = {}
    for f in features:
        uid = dsm.add_interface(f, f[:2])
        feature_uid_dict[f] = uid
    for r in entries:
        uids = dsm.add_entry(r)
        region_uid_dict[r] = uids
    for function in fat_report.function_entries.values():
        for region in function.interactions:
            for in_region, in_features in region.incommingRegions.items():
                dsm.add_connection(
                    region_uid_dict[in_region][1],
                    region_uid_dict[function.file_name][0],
                    interfaces=[feature_uid_dict[f] for f in set(in_features)]
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
        self, table_config: tp.Any, report_path: ReportFilepath,
        **table_kwargs: tp.Any
    ) -> None:
        super().__init__(table_config, **table_kwargs)
        self.report = FeatureArchitectureTaintReport(report_path.full_path())
        self.revision = report_path.report_filename.commit_hash
        self.data = fat_report_to_table(self.report)
        self.dsm = fat_report_to_DSM(self.report)


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
    TableGenerator, generator_name="fat-dsm", options=[REQUIRE_CASE_STUDY]
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
