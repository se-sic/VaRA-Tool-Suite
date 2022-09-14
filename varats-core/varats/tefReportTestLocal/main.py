from varats.report.tef_report import TEFReport
from varats.report.tef_report import TEFReportAggregate
import json
import typing as tp
from enum import Enum
from pathlib import Path

# Press the green button in the gutter to run the script.
tef_report_aggregate = TEFReportAggregate(Path("/home/aufrichtig/bachelor/XZCompressionLevel0.zip"))
tef_report_aggregate.wall_clock_times
print("test")

