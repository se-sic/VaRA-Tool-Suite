from varats.report.tef_report import TEFReport
from varats.report.tef_report import TEFReportAggregate
from varats.report.gnu_time_report import TimeReport, TimeReportAggregate
import json
import typing as tp
from enum import Enum
from pathlib import Path

# Press the green button in the gutter to run the script.
blackbox_test = TimeReportAggregate(Path("/home/aufrichtig/bachelor") / Path("XZCompressionLevel0.zip"))
print(blackbox_test.summary)
