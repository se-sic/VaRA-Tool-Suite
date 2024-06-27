"""This is a perf-script compatible script that writes overhead information in
yaml-format to stdout."""

from __future__ import print_function

import os
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
irrelevant_dsos = ["[kernel.kallsyms]", "[unknown]"]


def is_irrelevant_comm(comm: str) -> bool:
    if comm in irrelevant_comms:
        return True
    return False


def is_irrelevant_dso(dso: str) -> bool:
    if dso.startswith("/lib") or dso.startswith("/usr/lib"):
        return True

    if dso in irrelevant_dsos:
        return True

    return False


sample_data: tp.Dict[str, FunctionData] = {}
total_samples = 0


def trace_begin() -> None:
    pass


def trace_end() -> None:
    print(f"total_samples: {total_samples}")
    print("functions:")
    for func_data in sorted(
        sample_data.values(), key=lambda x: x.samples, reverse=True
    ):
        print(f"    {func_data.name}:")
        print(f"        samples: {func_data.samples}")
        print(
            f"        overhead: {(func_data.samples / total_samples) * 100:.2f}%"
        )
        print(f"        command: {func_data.command}")
        print(f"        dso: {func_data.dso}")


def process_event(param_dict: tp.Dict[str, tp.Any]) -> None:
    global total_samples

    func_name = param_dict["symbol"]
    command = param_dict["comm"]
    raw_dso = param_dict["dso"]
    dso = Path(raw_dso).name

    # ignore overhead of perf and gnu-time
    if is_irrelevant_comm(command):
        return

    total_samples += 1

    # do not collect stats for system libs and kernel functions
    if is_irrelevant_dso(raw_dso):
        return

    if func_name not in sample_data:
        sample_data[func_name] = FunctionData(func_name, command, dso)
    sample_data[func_name].add_sample()
