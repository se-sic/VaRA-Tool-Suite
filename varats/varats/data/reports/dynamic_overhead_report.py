from varats.report.report import BaseReport
from pathlib import Path
from collections import defaultdict


class DynamicOverheadReport(
    BaseReport, shorthand="DynOverhead", file_type="txt"
):

    class RegionCounter:

        def __init__(self):
            self.__in = 0
            self.__out = 0

        def enter(self):
            self.__in += 1

        def leave(self):
            self.__out += 1

        def isvalid(self):
            return self.__in == self.__out

        def count_visited(self):
            return self.__in

    def __init__(self, path: Path):
        super().__init__(path)
        self.__entries = defaultdict(DynamicOverheadReport.RegionCounter)

        for line in open(path, "r"):
            try:
                command, id = line.split()
                if command == "Entering":
                    self.__entries[id].enter()
                elif command == "Leaving":
                    self.__entries[id].leave()
            except ValueError:
                continue

        self.__total_region_count = 0

        # Generate report
        for region in self.__entries.values():
            if region.isvalid():
                self.__total_region_count += region.count_visited()

    def isvalid(self) -> bool:
        return all(v.isvalid() for v in self.__entries.values())

    def regions_visited(self):
        return self.__total_region_count
