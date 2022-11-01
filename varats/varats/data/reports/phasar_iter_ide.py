import shutil
import typing as tp
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from varats.report.gnu_time_report import TimeReportAggregate
from varats.report.report import BaseReport


class PhasarBCStats():

    def __init__(self, path: Path) -> None:
        with open(path, "r", encoding="utf-8") as stats_file:
            for line in stats_file.readlines():
                if line.startswith("> Instructions"):
                    self._num_instructions = int(line.split(":")[1])

    @property
    def num_instructions(self) -> int:
        return self._num_instructions


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
