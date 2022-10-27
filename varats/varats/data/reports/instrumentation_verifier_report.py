"""Instrumentation verifier report implementation for checkif if projects get
correctly instrumented."""

from varats.report.report import BaseReport


class InstrVerifierReport(BaseReport, shorthand="IVR", file_type="txt"):
    """An instrumentation verifier report for testing how well project where
    instrumented."""