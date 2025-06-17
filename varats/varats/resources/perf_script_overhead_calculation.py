"""This is a perf-script compatible script that writes overhead information in
yaml-format to stdout."""

from __future__ import print_function

import os
import pprint
import sys
import typing as tp
from pathlib import Path

sys.path.append(os.environ['PERF_EXEC_PATH'] + \
  '/scripts/python/Perf-Trace-Util/lib/Perf/Trace')

from Core import *
from perf_trace_context import *


class FunctionData:

    def __init__(self, name: str, command: str, dso: str) -> None:
        self.__name = name
        self.__command = command
        self.__dso = dso
        self.__samples = 0

    @property
    def name(self) -> str:
        return self.__name

    @property
    def command(self) -> str:
        return self.__command

    @property
    def dso(self) -> str:
        return self.__dso

    @property
    def samples(self) -> int:
        return self.__samples

    def add_sample(self) -> None:
        self.__samples += 1


irrelevant_comms = ["perf-exec", "time"]


def is_irrelevant_comm(comm: tp.Union[str, None]) -> bool:
    return comm is None or comm in irrelevant_comms


def is_irrelevant_dso(dso: tp.Union[str, None]) -> bool:
    if dso is None:
        return True

    if dso.startswith("/lib") or dso.startswith("/usr/lib"):
        return True

    # kernel module functions and some other irrelevant entries
    # are encapsulated in brackets
    if dso[0] == "[" and dso[-1] == "]":
        return True

    return False


sample_data: tp.Dict[str, FunctionData] = {}
total_samples = 0
processed_samples = 0
skipped_samples = 0
irrelevant_samples = 0
missing_data_samples = 0


def trace_begin() -> None:
    pass


def trace_end() -> None:
    print(f"total_samples: {total_samples}")
    print(f"processed_samples: {processed_samples}")
    print(f"skipped_samples: {skipped_samples}")
    print(f"missing_data_samples: {missing_data_samples}")
    print(f"irrelevant_samples: {irrelevant_samples}")
    print("functions:")
    for func_data in sorted(
        sample_data.values(), key=lambda x: x.samples, reverse=True
    ):
        print(f"    {func_data.name}:")
        print(f"        samples: {func_data.samples}")
        print(f"        overhead: {(func_data.samples / total_samples):.4f}")
        print(f"        command: {func_data.command}")
        print(f"        dso: {func_data.dso}")


def process_event(param_dict: tp.Dict[str, tp.Any]) -> None:
    global total_samples
    global processed_samples
    global skipped_samples
    global irrelevant_samples
    global missing_data_samples

    total_samples += 1

    func_name = param_dict.get("symbol")
    command = param_dict.get("comm")
    raw_dso = param_dict.get("dso")
    callchain = param_dict.get("callchain")

    # Ignore overhead of perf and gnu-time.
    if is_irrelevant_comm(command):
        skipped_samples += 1
        return

    processed_samples += 1

    # Use callchain to attribute samples from system libraries to the dso
    # under investigation.
    if is_irrelevant_dso(raw_dso) and callchain is not None:
        for entry in callchain:
            entry_dso = entry.get("dso")
            entry_sym = entry.get("sym")
            entry_name = entry_sym.get("name") if entry_sym else None
            if entry_dso and entry_name and not is_irrelevant_dso(entry_dso):
                raw_dso = entry_dso
                func_name = entry_name
                break

    if None in (func_name, raw_dso):
        print(f"[WARNING] Skipping sample with missing data.", file=sys.stderr)
        if os.environ.get("LOG_LEVEL", "WARNING").upper() == "DEBUG":
            pprint.pp(param_dict, indent=2, compact=True, stream=sys.stderr)
        missing_data_samples += 1
        return

    # Do not collect stats for system libs and kernel functions.
    if is_irrelevant_dso(raw_dso):
        irrelevant_samples += 1
        return

    if func_name not in sample_data:
        dso = Path(raw_dso).name
        sample_data[func_name] = FunctionData(func_name, command, dso)

    sample_data[func_name].add_sample()
