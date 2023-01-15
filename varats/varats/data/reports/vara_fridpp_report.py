"""Implements report for VaRA's InstrumentationPointPrinter utility pass."""
import typing as tp
from pathlib import Path

from varats.report.report import BaseReport


class FeatureRegionEntry:

    def __init__(
        self, name: str, uuid: str, function_relative_id: str,
        last_modifying_commit: str
    ):
        self.__name = name
        self.__uuid = uuid
        self.__function_relative_id = function_relative_id
        self.__last_modifying_commit = last_modifying_commit

    @property
    def name(self) -> str:
        return self.__name

    @property
    def uuid(self) -> str:
        return self.__uuid

    @property
    def function_relative_id(self) -> str:
        return self.__function_relative_id

    @property
    def last_modifying_commit(self) -> str:
        return self.__last_modifying_commit

    def __str__(self) -> str:
        return f"""{{
            name: {self.name}
            uuid: {self.uuid}
            function_relative_id: {self.function_relative_id}
            last_modifying_commit: {self.last_modifying_commit}
        }}
        """


class VaraFRIDPPReport(BaseReport, shorthand="VaraFRIDPP", file_type="txt"):
    """Report for VaRA's FuncRelativeIDPrinter utility pass, which prints the
    source code locations of instrumentation points of feature regions."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.__feature_regions = None
        self.__count_feature_regions = None
        self._parse_report()

    @property
    def feature_regions(self) -> tp.Dict[str, FeatureRegionEntry]:
        return self.__feature_regions

    def get_fr_entry(self, uuid: str) -> FeatureRegionEntry:
        return self.__feature_regions[uuid]

    def get_function_relative_id_by_uuid(self, uuid: str) -> str:
        if uuid in self.__feature_regions:
            return self.__feature_regions[uuid].function_relative_id
        else:
            return "Base"

    def count_feature_regions(self, function_relative_id_base: str) -> int:
        if function_relative_id_base in self.__count_feature_regions:
            return self.__count_feature_regions[function_relative_id_base]
        else:
            return 0

    def _parse_report(self) -> None:
        feature_regions = {}
        count_feature_regions = {}
        with open(self.path, "r") as f:
            for line in f:
                line = line.strip()
                if line == "BEGIN region list." or line == "END region list.":
                    continue
                if line == "FeatureRegion":
                    name = next(f).strip().replace("Name: ", "")
                    uuid = next(f).strip().replace("UUID: ", "")
                    function_relative_id = next(f).strip().replace(
                        "FunctionRelativeID: ", ""
                    )
                    function_relative_id_base = function_relative_id.rsplit(
                        "_", 1
                    )[0]
                    if function_relative_id_base in count_feature_regions:
                        count_feature_regions[function_relative_id_base] += 1
                    else:
                        count_feature_regions[function_relative_id_base] = 1
                    last_modifying_commit = next(f).strip().replace(
                        "LastModifyingCommit: ", ""
                    )
                    feature_regions[uuid] = FeatureRegionEntry(
                        name, uuid, function_relative_id, last_modifying_commit
                    )
        feature_regions["0"] = FeatureRegionEntry("Base", "0", "None", "None")
        self.__feature_regions: tp.Dict[str,
                                        FeatureRegionEntry] = feature_regions
        self.__count_feature_regions: tp.Dict[str, int] = count_feature_regions
