Data handling
=============

* :ref:`reports`
* :ref:`Handling utilities for generated report files`
* :ref:`data management`
* :ref:`Data providers`

Reports
-------

VaRA-TS manages experiment result data in the form of reports.
The report file contains all generated data during the experiment and the report class gives the user an interface to interact with the data.
To simplify report handling and storage management, the report base classes provide functionality to automatically create customized filenames.
In each filename, the framework encodes information like report type, project, revision, and a UUID, to specify the run that created the file.
Furthermore, report implementers have the option to customize the filename even further.

As a simple example and help to implement your own report, take a look at the :ref:`EmptyReport`.

.. toctree::
    :maxdepth: 1
    :caption: List of provided report classes

    data_reports/empty_report
    data_reports/blame_report

Report module
.............

.. automodule:: varats.data.report
    :members:
    :undoc-members:
    :show-inheritance:

-----

Handling utilities for generated report files
.............................................

.. automodule:: varats.data.revisions
    :members:
    :undoc-members:
    :show-inheritance:

-----

Data management
---------------

Report data can be accessed via different :class:`~varats.data.databases.database.Database` classes.
Each concrete database class offers its data in form of a pandas dataframe with a specific layout.
Clients can query them for the data for a specific project or case study via the function ``get_data_for_project``.
The database class then takes care of :class:`loading<varats.data.data_manager.DataManager>` and :func:`caching<varats.data.cache_helper.build_cached_report_table>` the relevant result files.

You can add new database classes by creating a subclass of :class:`~varats.data.databases.database.Database` in a separate module in the directory ``varats/data/databases``.

.. toctree::
    :maxdepth: 1
    :caption: The following databases are currently available:

    data_databases/blame_interaction_database
    data_databases/blame_interaction_degree_database
    data_databases/commit_interaction_database


Module: database
....................

.. automodule:: varats.data.databases.database
    :members:
    :undoc-members:
    :show-inheritance:

-----

Module: cache_helper
....................

.. automodule:: varats.data.cache_helper
    :members:
    :undoc-members:
    :show-inheritance:

-----

Module: data_manager
......................

.. automodule:: varats.data.data_manager
    :members:
    :undoc-members:
    :show-inheritance:

-----

Module: version_header
......................

.. automodule:: varats.data.version_header
    :members:
    :undoc-members:
    :show-inheritance:

-----

Data providers
--------------

Providers are a means to supply additional data for a :ref:`project<Projects>`.
For example, the :ref:`CVE provider` allows access to all CVEs that are related to a project.

You can implement your own provider by creating a subclass of :class:`~varats.data.provider.provider.Provider` in its own subdirectory of ``data/provider``.
There is no restriction on the format in which data has to be provided.
The ``Provider`` abstract class only requires you to specify how to create an instance of your provider for a specific project, as well as a fallback implementation (that most likely returns no data).
If your provider needs some project-specific implementation, create a class with the name ``<your_provider_class>Hook`` and make the projects inherit from it, similar to the :class:`~varats.data.provider.cve.cve_provider.CVEProviderHook`.
If a project does not inherit from that hook, your provider's :func:`~varats.data.provider.provider.Provider.create_provider_for_project` should return ``None``.
In that case, the :func:`provider factory method<varats.data.provider.provider.Provider.get_provider_for_project>` falls back to your default provider implementation and issues a warning.
For an example provider implementation take a look at the :ref:`CVE provider`.



.. toctree::
    :maxdepth: 1
    :caption: List of supported providers

    data_providers/cve_provider
    data_providers/release_provider

Provider module
...............

.. automodule:: varats.data.provider.provider
    :members:
    :undoc-members:
    :show-inheritance:
