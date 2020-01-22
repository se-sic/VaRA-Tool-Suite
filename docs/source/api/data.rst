Data handling
=============

* :ref:`reports`
* :ref:`data handling utilitis`

Reports
-----------

VaRA-TS manages experiment result data in the form of reports.
The report file contains all generated data during the experiment and the report class gives the user a interface to interact with the data.
To simplify report handling and storage management, the report base classes provide functionality to automatically create customized filenames.
In each filename the framework encodes information like report type, project, revision, and a UUID, to specify the run that created the file.
Furthermore, report implementers have the option to customize the filename even further.

As a simple example and help to implement your own report, take a look at the :ref:`EmptyReport`.

.. toctree::
    :maxdepth: 2
    :caption: List of provided report classes

    data_reports/empty_report
    data_reports/blame_report

Report module
.............

.. automodule:: varats.data.report
    :members:
    :undoc-members:
    :show-inheritance:

Data handling utilities
-----------------------

Module: cache_helper
....................

.. automodule:: varats.data.cache_helper
    :members:
    :undoc-members:
    :show-inheritance:

Module: version_header
......................

.. automodule:: varats.data.version_header
    :members:
    :undoc-members:
    :show-inheritance:

