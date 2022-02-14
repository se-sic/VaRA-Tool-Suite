"""Report moduel for phasar incremental analysis reports."""
import os
import shutil
import tempfile
import typing as tp
from enum import Enum
from pathlib import Path
from statistics import mean

import yaml

from varats.report.report import BaseReport, FileStatusExtension, ReportFilename


class AnalysisType(Enum):

    value: str

    TYPE_STATE = "typestate"
    TAINT = "taint"
    LCA = "ide-lca"

    @staticmethod
    def convert_from(value: str) -> tp.List['AnalysisType']:
        enabled_analysis_types = []
        for analysis_type in AnalysisType:
            if analysis_type.value in value:
                enabled_analysis_types.append(analysis_type)

        return enabled_analysis_types

    def __str__(self) -> str:
        return f"{self.value}"


class IncrementalTimings():
    """
    ---
    INC_INITIAL_PT_CONSTRUCTION_TIME: 1000
    INC_INITIAL_ICFG_CONSTRUCTION_TIME: 1000
    INC_INITIAL_IRDB_CONSTRUCTION_TIME: 1000
    INC_INITIAL_TH_CONSTRUCTION_TIME: 1000
    INC_INCREMENTAL_IRDB_CONSTRUCTION_TIME: 1000

    WPA_PT_CONSTRUCTION_TIME: 1000
    WPA_ICFG_CONSTRUCTION_TIME: 1000
    WPA_TH_CONSTRUCTION_TIME: 1000
    WPA_IRDB_CONSTRUCTION_TIME: 1000
    ...

    * WPA_IRDB_CONSTRUCTION_TIME
    * WPA_TH_CONSTRUCTION_TIME
    * WPA_PT_CONSTRUCTION_TIME
    * WPA_ICFG_CONSTRUCTION_TIME
    * WPA_DFA_TEST_SOLVING_TIME


    * INC_INITIAL_IRDB_CONSTRUCTION_TIME
    * INC_INITIAL_TH_CONSTRUCTION_TIME
    * INC_INITIAL_PT_CONSTRUCTION_TIME
    * INC_INITIAL_ICFG_CONSTRUCTION_TIME
    * INC_INITIAL_DFA_SOLVING_TIME


    * INC_INCREMENTAL_IRDB_CONSTRUCTION_TIME
    * INC_INCREMENTAL_DELTA_CONSTRUCTION_TIME
    * INC_INCREMENTAL_IR_REMAP_TIME

    * INC_INCREMENTAL_TH_CONSTRUCTION_TIME
    * INC_INCREMENTAL_PT_CONSTRUCTION_TIME
    * INC_INCREMENTAL_ICFG_CONSTRUCTION_TIME
    * INC_INCREMENTAL_DFA_SOLVING_TIME

    """

    @staticmethod
    def create_empty_report() -> 'IncrementalTimings':
        return IncrementalTimings(None)

    def __init__(self, path: tp.Optional[Path]) -> None:
        self.__wpa_irdb_construction_time = []
        self.__wpa_th_construction_time = []
        self.__wpa_pt_construction_time = []
        self.__wpa_icfg_construction_time = []
        self.__wpa_dfa_test_solving_time = []
        self.__inc_initial_irdb_construction_time = []
        self.__inc_initial_th_construction_time = []
        self.__inc_initial_pt_construction_time = []
        self.__inc_initial_icfg_construction_time = []
        self.__inc_initial_dfa_solving_time = []
        self.__inc_incremental_irdb_construction_time = []
        self.__inc_incremental_delta_construction_time = []
        self.__inc_incremental_ir_remap_time = []
        self.__inc_incremental_th_construction_time = []
        self.__inc_incremental_pt_construction_time = []
        self.__inc_incremental_icfg_construction_time = []
        self.__inc_incremental_dfa_solving_time = []

        if not path:
            return

        with open(path, 'r') as stream:
            documents = yaml.load_all(stream, Loader=yaml.CLoader)
            for doc in documents:
                for line in doc:
                    if line == 'WPA_IRDB_CONSTRUCTION_TIME':
                        self.__wpa_irdb_construction_time.append(
                            float(doc[line])
                        )
                    if line == 'WPA_TH_CONSTRUCTION_TIME':
                        self.__wpa_th_construction_time.append(float(doc[line]))

                    if line == 'WPA_PT_CONSTRUCTION_TIME':
                        self.__wpa_pt_construction_time.append(float(doc[line]))
                    if line == 'WPA_ICFG_CONSTRUCTION_TIME':
                        self.__wpa_icfg_construction_time.append(
                            float(doc[line])
                        )
                    if line == 'WPA_DFA_TEST_SOLVING_TIME':
                        self.__wpa_dfa_test_solving_time.append(
                            float(doc[line])
                        )
                    if line == 'INC_INITIAL_IRDB_CONSTRUCTION_TIME':
                        self.__inc_initial_irdb_construction_time.append(
                            float(doc[line])
                        )
                    if line == 'INC_INITIAL_TH_CONSTRUCTION_TIME':
                        self.__inc_initial_th_construction_time.append(
                            float(doc[line])
                        )
                    if line == 'INC_INITIAL_PT_CONSTRUCTION_TIME':
                        self.__inc_initial_pt_construction_time.append(
                            float(doc[line])
                        )
                    if line == 'INC_INITIAL_ICFG_CONSTRUCTION_TIME':
                        self.__inc_initial_icfg_construction_time.append(
                            float(doc[line])
                        )
                    if line == 'INC_INITIAL_DFA_SOLVING_TIME':
                        self.__inc_initial_dfa_solving_time.append(
                            float(doc[line])
                        )
                    if line == 'INC_INCREMENTAL_IRDB_CONSTRUCTION_TIME':
                        self.__inc_incremental_irdb_construction_time.append(
                            float(doc[line])
                        )
                    if line == 'INC_INCREMENTAL_DELTA_CONSTRUCTION_TIME':
                        self.__inc_incremental_delta_construction_time.append(
                            float(doc[line])
                        )
                    if line == 'INC_INCREMENTAL_IR_REMAP_TIME':
                        self.__inc_incremental_ir_remap_time.append(
                            float(doc[line])
                        )
                    if line == 'INC_INCREMENTAL_TH_CONSTRUCTION_TIME':
                        self.__inc_incremental_th_construction_time.append(
                            float(doc[line])
                        )
                    if line == 'INC_INCREMENTAL_PT_CONSTRUCTION_TIME':
                        self.__inc_incremental_pt_construction_time.append(
                            float(doc[line])
                        )
                    if line == 'INC_INCREMENTAL_ICFG_CONSTRUCTION_TIME':
                        self.__inc_incremental_icfg_construction_time.append(
                            float(doc[line])
                        )
                    if line == 'INC_INCREMENTAL_DFA_SOLVING_TIME':
                        self.__inc_incremental_dfa_solving_time.append(
                            float(doc[line])
                        )

    @property
    def wpa_irdb_construction_time(self) -> float:
        return self.__mean(self.__wpa_irdb_construction_time)

    @property
    def wpa_th_construction_time(self) -> float:
        return self.__mean(self.__wpa_th_construction_time)

    @property
    def wpa_pt_construction_time(self) -> float:
        return self.__mean(self.__wpa_pt_construction_time)

    @property
    def wpa_icfg_construction_time(self) -> float:
        return self.__mean(self.__wpa_icfg_construction_time)

    @property
    def wpa_dfa_test_solving_time(self) -> float:
        return self.__mean(self.__wpa_dfa_test_solving_time)

    def total_wpa(self) -> float:
        return self.wpa_irdb_construction_time + \
            self.wpa_th_construction_time + \
            self.wpa_pt_construction_time + \
            self.wpa_icfg_construction_time + \
            self.wpa_dfa_test_solving_time

    @property
    def inc_initial_irdb_construction_time(self) -> float:
        return self.__mean(self.__inc_initial_irdb_construction_time)

    @property
    def inc_initial_th_construction_time(self) -> float:
        return self.__mean(self.__inc_initial_th_construction_time)

    @property
    def inc_initial_pt_construction_time(self) -> float:
        return self.__mean(self.__inc_initial_pt_construction_time)

    @property
    def inc_initial_icfg_construction_time(self) -> float:
        return self.__mean(self.__inc_initial_icfg_construction_time)

    @property
    def inc_initial_dfa_solving_time(self) -> float:
        return self.__mean(self.__inc_initial_dfa_solving_time)

    def total_initial(self) -> float:
        return self.inc_initial_irdb_construction_time + \
            self.inc_initial_th_construction_time + \
            self.inc_initial_pt_construction_time + \
            self.inc_initial_icfg_construction_time + \
            self.inc_initial_dfa_solving_time

    @property
    def inc_incremental_irdb_construction_time(self) -> float:
        return self.__mean(self.__inc_incremental_irdb_construction_time)

    @property
    def inc_incremental_delta_construction_time(self) -> float:
        return self.__mean(self.__inc_incremental_delta_construction_time)

    @property
    def inc_incremental_ir_remap_time(self) -> float:
        return self.__mean(self.__inc_incremental_ir_remap_time)

    @property
    def inc_incremental_th_construction_time(self) -> float:
        return self.__mean(self.__inc_incremental_th_construction_time)

    @property
    def inc_incremental_pt_construction_time(self) -> float:
        return self.__mean(self.__inc_incremental_pt_construction_time)

    @property
    def inc_incremental_icfg_construction_time(self) -> float:
        return self.__mean(self.__inc_incremental_icfg_construction_time)

    @property
    def inc_incremental_dfa_solving_time(self) -> float:
        return self.__mean(self.__inc_incremental_dfa_solving_time)

    def total_incremental(self) -> float:
        return self.inc_incremental_irdb_construction_time + \
            self.inc_incremental_th_construction_time + \
            self.inc_incremental_pt_construction_time + \
            self.inc_incremental_icfg_construction_time + \
            self.inc_incremental_dfa_solving_time

    @staticmethod
    def __mean(values: tp.List[float]) -> float:
        if len(values) == 0:
            return float('nan')

        return mean(values)

    def __str__(self) -> str:
        string = f"""WPA_IRDB_CONSTRUCTION_TIME              = {self.wpa_irdb_construction_time}
WPA_TH_CONSTRUCTION_TIME                = {self.wpa_th_construction_time}
WPA_PT_CONSTRUCTION_TIME                = {self.wpa_pt_construction_time}
WPA_ICFG_CONSTRUCTION_TIME              = {self.wpa_icfg_construction_time}
WPA_DFA_TEST_SOLVING_TIME               = {self.wpa_dfa_test_solving_time}
INC_INITIAL_IRDB_CONSTRUCTION_TIME      = {self.inc_initial_irdb_construction_time}
INC_INITIAL_TH_CONSTRUCTION_TIME        = {self.inc_initial_th_construction_time}
INC_INITIAL_PT_CONSTRUCTION_TIME        = {self.inc_initial_pt_construction_time}
INC_INITIAL_ICFG_CONSTRUCTION_TIME      = {self.inc_initial_icfg_construction_time}
INC_INITIAL_DFA_SOLVING_TIME            = {self.inc_initial_dfa_solving_time}
INC_INCREMENTAL_IRDB_CONSTRUCTION_TIME  = {self.inc_incremental_irdb_construction_time}
INC_INCREMENTAL_DELTA_CONSTRUCTION_TIME = {self.inc_incremental_delta_construction_time}
INC_INCREMENTAL_IR_REMAP_TIME           = {self.inc_incremental_ir_remap_time}
INC_INCREMENTAL_TH_CONSTRUCTION_TIME    = {self.inc_incremental_th_construction_time}
INC_INCREMENTAL_PT_CONSTRUCTION_TIME    = {self.inc_incremental_pt_construction_time}
INC_INCREMENTAL_ICFG_CONSTRUCTION_TIME  = {self.inc_incremental_icfg_construction_time}
INC_INCREMENTAL_DFA_SOLVING_TIME        = {self.inc_incremental_dfa_solving_time}"""
        return string


class IncrementalReport(BaseReport, shorthand="Inc", file_type="zip"):
    """Report for phasar incremental analysis results."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.__ide_lca_timings = IncrementalTimings.create_empty_report()
        self.__ide_typestate_timings = IncrementalTimings.create_empty_report()
        self.__ifds_taint_timings = IncrementalTimings.create_empty_report()

        with tempfile.TemporaryDirectory() as tmp_result_dir:
            shutil.unpack_archive(path, extract_dir=Path(tmp_result_dir))

            for res_file in Path(tmp_result_dir).iterdir():
                print(f"{res_file=}")
                if str(res_file
                      ).endswith('IDELinearConstantAnalysis-timings.yml'):
                    self.__ide_lca_timings = IncrementalTimings(res_file)

                if str(res_file).endswith('PlaceHolderTypestate-timings.yml'):
                    self.__ide_typestate_timings = IncrementalTimings(res_file)

                if str(res_file).endswith('PlaceHolderTaint-timings.yml'):
                    self.__ifds_taint_timings = IncrementalTimings(res_file)

            # TODO: impl actual file handling
            collected_files = []
            for (dirpath, dirnames, filenames) in os.walk(Path(tmp_result_dir)):
                collected_files.extend(filenames)

                break

            print(f"Found files: {collected_files}")

    def ide_lca_timings(self) -> IncrementalTimings:
        return self.__ide_lca_timings

    def ide_typestate_timings(self) -> IncrementalTimings:
        return self.__ide_typestate_timings

    def ifds_taint_timings(self) -> IncrementalTimings:
        return self.__ifds_taint_timings
