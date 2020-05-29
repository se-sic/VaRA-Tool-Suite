Testing
=======

Tests for the VaRA tool suite are located in the ``tests`` directory.
The tests are run using `pytest` but most of the tests are written using `unittest` syntax.

Mocking the vara configuration
------------------------------

To ensure a flawless test execution, it is important that the order of test execution does not matter, i.e. each single test is idempotent and does not modify the environment.
One common problem with this are the vara and benchbuild configurations, as they are stored in a single global object.
We therefore provide a helper function :func:`~tests.test_utils.replace_config()` to set a test-specific vara (and if needed benchbuild) configuration that can be safely modified without affecting other tests.
This function can be either used as a decorator similar to ``unittest.mock`` or as a context manager.

Test resources
--------------

Test resources, like report files or case studies, can be stored in the ``tests/TEST_INPUTS`` directory.
This directory follows the same structure one would also use for the tool-suites installation environment.
The path to this directory can be accessed via the :attr:`~tests.test_utils.TEST_INPUTS_DIR` attribute.
If using the :func:`~tests.test_utils.replace_config()` wrapper or context manager without providing an own configuration, the relevant paths in the replaced configuration object are already pointed to this environment.
Keep the data put in this directory as small as possible to avoid bloating the repository.

.. warning::
    Make sure that your tests *do not write to this directory* to maintain an idempotent test environment.
    If you really need to write files, use `temporary directories` instead.

-----

Module: test_utils
..................

.. automodule:: tests.test_utils
    :members:
    :undoc-members:
    :show-inheritance:
