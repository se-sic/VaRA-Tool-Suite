EmptyReport
===========

.. automodule:: varats.data.reports.empty_report
    :members:
    :undoc-members:
    :show-inheritance:


The :class:`~varats.data.reports.empty_report.EmptyReport` is a demonstrator
for the minimal viable report, providing all the basic functionality that is
needed by an experiment. However, to be actually useful for further data
processing, a report should also implement the constructor `__init__(self,
path: Path)`, which loads the report data from the given file and makes it
accessible through the reports API.

.. literalinclude:: ../../../../varats/varats/data/reports/empty_report.py
    :lines: 3-10
