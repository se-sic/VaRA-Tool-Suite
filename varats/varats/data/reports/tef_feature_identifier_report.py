import json
import typing as tp
from collections import defaultdict
from pathlib import Path

from varats.report.report import BaseReport

RegionTupleTy = tp.Tuple[frozenset, int]
PatchesTupleTy = tp.Tuple[str, int]


class TEFFeatureIdentifierReport(
    BaseReport, shorthand="TEFID", file_type=".json"
):

    def __init__(self, path: Path):
        super().__init__(path)

        self.__patch_names: tp.Set[str] = set()
        self.__patch_to_regions: tp.Dict[str, tp.Set[RegionTupleTy]] = dict()
        self.__regions_to_patches = defaultdict(list)
        self.__baseline_regions: tp.List = list()

        with open(self.path, "r") as report:
            results = json.load(report)

            for entry in results:
                if entry == "Baseline":
                    self.__baseline_regions = set()
                    for r in results[entry]:
                        self.__baseline_regions.add(
                            (frozenset(r.split('*')), results[entry][r])
                        )
                    continue

                patch_name = entry[len("PATCHED_"):]

                self.__patch_names.add(patch_name)
                self.__patch_to_regions[patch_name] = set()

                for region in results[entry]:
                    regions = frozenset(region.split('*'))
                    self.__patch_to_regions[patch_name].add(
                        (regions, results[entry][region])
                    )
                    self.__regions_to_patches[regions].append(
                        (patch_name, regions, results[entry][region])
                    )

    @property
    def patch_names(self) -> tp.Set[str]:
        return self.__patch_names

    @property
    def baseline_regions(self) -> tp.Set[RegionTupleTy]:
        return self.__baseline_regions

    @property
    def affectable_regions(self):
        return self.__regions_to_patches.keys()

    def regions_for_patch(self, patch_name: str) -> tp.Set[RegionTupleTy]:
        return self.__patch_to_regions[patch_name]

    def patches_containing_region(
        self, regions: tp.Iterable[str]
    ) -> tp.List[tp.Tuple[str, frozenset, int]]:
        result = []
        regions = frozenset(regions)
        for region in self.__regions_to_patches:
            if regions.issubset(region):
                result += self.__regions_to_patches[region]
        return result

    def patches_for_regions(
        self, regions: tp.Iterable[str]
    ) -> tp.List[tp.Tuple[str, frozenset, int]]:
        regions = frozenset(regions)
        if regions in self.__regions_to_patches:
            return self.__regions_to_patches[regions]
        return []
