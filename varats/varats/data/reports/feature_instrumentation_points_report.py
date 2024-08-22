"""Report for VaRA's InstrumentationPointPrinter utility pass."""
import typing as tp
from pathlib import Path

from varats.report.report import BaseReport


class FeatureInstrumentationPointsReport(
    BaseReport, shorthand="FIP", file_type="txt"
):
    """Report for VaRA's InstrumentationPointPrinter utility pass, which prints
    information about the instrumentation points of feature regions."""

    def __init__(self, report_file: Path):
        super().__init__(report_file)

        self.__feature_regions = {}
        with open(report_file, "r") as file:
            while line := file.readline():
                if not line.startswith("FeatureRegion"):
                    continue

                # The two lines after the FeatureRegion line contain the UUID and the feature name
                uuid_line = file.readline()
                feature_name_line = file.readline()

                uuid = int(uuid_line.split(": ")[1].strip())
                feature_name = feature_name_line.split(": ")[1].strip().replace(
                    "FR(", ""
                ).replace(")", "")

                self.__feature_regions[uuid] = feature_name

    def feature_regions(self) -> tp.Set[int]:
        return set(self.__feature_regions.keys())

    def feature_names(self) -> tp.Set[str]:
        return set(self.__feature_regions.values())

    def regions_for_feature(self, feature_name: str) -> tp.Set[int]:
        return {
            uuid for uuid, name in self.__feature_regions.items()
            if name == feature_name
        }

    def feature_name_for_region(self, region_uuid: int) -> str:
        return self.__feature_regions[region_uuid]
