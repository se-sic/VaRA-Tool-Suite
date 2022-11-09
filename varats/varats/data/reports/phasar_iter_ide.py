import shutil
import typing as tp
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from varats.report.gnu_time_report import TimeReportAggregate
from varats.report.report import BaseReport


class PhasarBCStats():

    def __init__(self, path: Path) -> None:
        self._num_instructions = -1

        with open(path, "r", encoding="utf-8") as stats_file:
            for line in stats_file.readlines():
                if line.startswith("> Instructions"):
                    self._num_instructions = int(line.split(":")[1])

    @property
    def num_instructions(self) -> int:
        return self._num_instructions


class ResultCompare():

    def __init__(self, path: Path) -> None:
        found_match = False
        found_not_match = False
        with open(path, "r", encoding="utf-8") as stats_file:
            for line in stats_file.readlines():
                if line.startswith("The results do not match!"):
                    found_not_match = True

                if line.startswith("The results do match!"):
                    found_match = True

        if found_match and found_not_match:
            raise AssertionError(
                "File contained mixed information wrong/wright results "
                "at the same time"
            )

        # if not found_match and not found_not_match:
        #     raise AssertionError("File did not contain cmp data")

        if found_match:
            self._results_match = True
        else:
            self._results_match = False

    @property
    def results_match(self) -> bool:
        return self._results_match


class PhasarIterIDEStatsReport(
    BaseReport, shorthand="PIterIDEStats", file_type="zip"
):

    _bc_stats: tp.Optional[PhasarBCStats]
    _old_typestate: tp.Optional[TimeReportAggregate]
    _old_taint: tp.Optional[TimeReportAggregate]
    _old_lca: tp.Optional[TimeReportAggregate]
    _new_typestate: tp.Optional[TimeReportAggregate]
    _new_taint: tp.Optional[TimeReportAggregate]
    _new_lca: tp.Optional[TimeReportAggregate]

    def __init__(self, path: Path) -> None:
        self._bc_stats = None
        self._cmp_typestate = None
        self._cmp_taint = None
        self._cmp_lca = None
        self._old_typestate = None
        self._old_taint = None
        self._old_lca = None
        self._new_typestate = None
        self._new_taint = None
        self._new_lca = None

        with TemporaryDirectory() as tmpdir:
            shutil.unpack_archive(path, tmpdir)

            for file in Path(tmpdir).iterdir():
                if file.name.startswith("phasar_bc_stats"):
                    self._bc_stats = PhasarBCStats(file)
                elif file.name.startswith("cmp_typestate"):
                    self._cmp_typestate = ResultCompare(file)
                elif file.name.startswith("cmp_taint"):
                    self._cmp_taint = ResultCompare(file)
                elif file.name.startswith("cmp_lca"):
                    self._cmp_lca = ResultCompare(file)
                elif file.name.startswith("old_typestate"):
                    self._old_typestate = TimeReportAggregate(file)
                elif file.name.startswith("old_taint"):
                    self._old_taint = TimeReportAggregate(file)
                elif file.name.startswith("old_lca"):
                    self._old_lca = TimeReportAggregate(file)
                elif file.name.startswith("new_typestate"):
                    self._new_typestate = TimeReportAggregate(file)
                elif file.name.startswith("new_taint"):
                    self._new_taint = TimeReportAggregate(file)
                elif file.name.startswith("new_lca"):
                    self._new_lca = TimeReportAggregate(file)
                else:
                    print(f"Unknown file {file}!")

    @property
    def basic_bc_stats(self) -> tp.Optional[PhasarBCStats]:
        return self._bc_stats

    @property
    def cmp_typestate(self) -> tp.Optional[ResultCompare]:
        return self._cmp_typestate

    @property
    def cmp_taint(self) -> tp.Optional[ResultCompare]:
        return self._cmp_taint

    @property
    def cmp_lca(self) -> tp.Optional[ResultCompare]:
        return self._cmp_lca

    @property
    def old_typestate(self) -> tp.Optional[TimeReportAggregate]:
        return self._old_typestate

    @property
    def old_taint(self) -> tp.Optional[TimeReportAggregate]:
        return self._old_taint

    @property
    def old_lca(self) -> tp.Optional[TimeReportAggregate]:
        return self._old_lca

    @property
    def new_typestate(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_typestate

    @property
    def new_taint(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_taint

    @property
    def new_lca(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_lca
