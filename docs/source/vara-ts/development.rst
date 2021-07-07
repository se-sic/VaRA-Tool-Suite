Developing with VaRA-TS
=======================

First, take a look at our :ref:`install guide<Build VaRA with vara-buildsetup>` to learn how to set up the tool suite.

The :ref:`VaRA-TS API Reference` contains information about how to :ref:`work with the tool-suite<Tools>`, as well as how to add your own :ref:`research tools<Research Tool API>`, :ref:`experiments`, :ref:`reports`, :ref:`plots`, and more.

:ref:`Debugging with Visual Studio Code` shows an example on how to debug benchbuild projects and experiments using the VSCode debugger.

For further information about `benchbuild <https://github.com/PolyJIT/benchbuild>`_ related concepts, like `Experiments` or `Projects`, take a look at the  `benchbuild documentation <https://pprof-study.readthedocs.io/en/master/>`_.

Testing
-------

Tests for the VaRA tool suite are located in the ``tests`` directory.
The tests are run using `pytest` but most of the tests are written using `unittest` syntax.

Mocking the vara configuration
..............................

To ensure a flawless test execution, it is important that the order of test execution does not matter, i.e. each single test is idempotent and does not modify the environment.
One common problem with this are the vara and benchbuild configurations, as they are stored in a single global object.
We therefore provide a helper function :func:`~tests.test_utils.replace_config()` to set a test-specific vara (and if needed benchbuild) configuration that can be safely modified without affecting other tests.
This function can be either used as a decorator similar to ``unittest.mock`` or as a context manager.

Test resources
..............

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


-----

Debugging with Visual Studio Code
.................................

The .vscode/launch.json file in the VaRA-Tool-Suite repository contains a configuration for Visual Studio Code.
With `F5` the given example is executed.
It runs the command `benchbuild run -E JustCompile gzip` by default, which can be adapted to debug other projects and experiments by changing the arguments that are passed to `benchbuild`.
To step through the JustCompile experiment a breakpoint has to be set in just_compile.py.
`F9` can be used to set/unset a breakpoint at the current line.
