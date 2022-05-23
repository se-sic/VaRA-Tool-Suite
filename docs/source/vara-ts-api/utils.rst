Utility and helper modules
==========================

Utilities overview
------------------
* :ref:`Module: cli_util`
* :ref:`Module: html_util`
* :ref:`Module: util`
* :ref:`Module: exceptions`
* :ref:`Module: git_util`
* :ref:`Module: github_util`
* :ref:`Module: experiment_util`
* :ref:`Module: project_util`
* :ref:`Module: filesystem_util`
* :ref:`Module: logger_util`
* :ref:`Module: tool_util`

Module: cli_util
................

.. automodule:: varats.ts_utils.cli_util
    :members:
    :undoc-members:
    :show-inheritance:

.. raw:: html

    <hr>

Module: html_util
.................

.. automodule:: varats.ts_utils.html_util
    :members:
    :undoc-members:
    :show-inheritance:

.. raw:: html

    <hr>

Module: util
............

.. automodule:: varats.utils.util
    :members:
    :undoc-members:
    :show-inheritance:

.. raw:: html

    <hr>

Module: exceptions
..................

.. automodule:: varats.utils.exceptions
    :members:
    :undoc-members:
    :show-inheritance:

.. raw:: html

    <hr>

Module: git_util
................

.. automodule:: varats.utils.git_util
    :members:
    :undoc-members:
    :show-inheritance:

.. raw:: html

    <hr>

Module: github_util
...................

.. automodule:: varats.utils.github_util
    :members:
    :undoc-members:
    :show-inheritance:

.. raw:: html

    <hr>

Module: experiment_util
.......................

.. automodule:: varats.experiment.experiment_util
    :members:
    :undoc-members:
    :show-inheritance:

.. raw:: html

    <hr>

Module: project_util
....................

.. automodule:: varats.project.project_util
    :members:
    :undoc-members:
    :show-inheritance:

.. raw:: html

    <hr>

Module: filesystem_util
.......................

.. automodule:: varats.utils.filesystem_util
    :members:
    :undoc-members:
    :show-inheritance:

.. raw:: html

    <hr>

Module: cmake_util
..................

.. automodule:: varats.tools.research_tools.cmake_util
    :members:
    :undoc-members:
    :show-inheritance:

.. raw:: html

    <hr>

Logger usage
------------

By default, the tool suite logger shows only severity levels from `WARNING` up to `CRITICAL` on the console.
The log severity level can be configured by setting the environment variable ``LOG_LEVEL``.
So, for example, to get more information we can set the severity level to info by:

.. code-block:: bash

  LOG_LEVEL=info vara-buildsetup vara -i

How to add logging to a module
..............................

For the tool suite, we do module-level logging to make it easier to trace where log output comes from.
Hence, every module that logs something needs to set the logger to the current module name like this:

.. code-block:: python

  LOG = logging.getLogger(__name__)

What should be logged and how?
..............................

In general, the tool suite uses `print` for normal output that should always go to the user.
Logging is used to add additional information or highlight warning or error cases.
For logging categories, we follow the default python logging `HOWTO <https://docs.python.org/3/howto/logging.html>`_.

Module: logger_util
...................

.. automodule:: varats.utils.logger_util
    :members:
    :undoc-members:
    :show-inheritance:

.. raw:: html

    <hr>

Module: tool_util
.................

.. automodule:: varats.tools.tool_util
    :members:
    :undoc-members:
    :show-inheritance:
