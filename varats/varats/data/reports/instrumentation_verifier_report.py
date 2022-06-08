"""Instrumentation verifier report implementation for checkif if projects get
correctly instrumented."""

from pathlib import Path

from varats.report.report import BaseReport


class InstrVerifierReport(BaseReport, shorthand="IVR", file_type="txt"):
    """An instrumentation verifier report for testing how well project where
    instrumented."""

    def __init__(self, path: Path) -> None:
        print(f"called inst verifier init with {path}")
