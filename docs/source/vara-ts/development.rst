Developing with VaRA-TS
=======================

First, take a look at our :ref:`install guide<Build VaRA with vara-buildsetup>` to learn how to set up the tool suite.

The :ref:`VaRA-TS API Reference` contains information about how to :ref:`work with the tool-suite<Tools Overview>`, as well as how to add your own :ref:`research tools<Research Tool API>`, :ref:`experiments`, :ref:`reports`, :ref:`plots`, and more.

:ref:`Debugging with Visual Studio Code` shows an example on how to debug benchbuild projects and experiments using the VSCode debugger.

For further information about `benchbuild <https://github.com/PolyJIT/benchbuild>`_ related concepts, like `Experiments` or `Projects`, take a look at the  `benchbuild documentation <https://pprof-study.readthedocs.io/en/master/>`_.

Pre-Commit
----------

We use `pre-commit <https://pre-commit.com/>`__ to automatically enforce our code-style guidelines.
To activate these checks, you first have to install pre-commit and its hooks:

.. code-block:: console

    pip install pre-commit
    pre-commit install

Afterwards, the checks will run every time you make a ``git commit``.
The same checks also run in our CI and pull requests are required to pass them before merging.
It is also possible to run the checks manually:

.. code-block:: console

    pre-commit run --all-files

Testing
-------

Tests for the VaRA tool suite are located in the ``tests`` directory.
The tests are run using `pytest` but most of the tests are written using `unittest` syntax.

Mocking the vara configuration
..............................

To ensure a flawless test execution, it is important that the order of test execution does not matter, i.e. each single test is idempotent and does not modify the environment.
One common problem with this are the vara and benchbuild configurations, as they are stored in a single global object.
We therefore provide a helper function :func:`~tests.helper_utils.replace_config()` to set a test-specific vara (and if needed benchbuild) configuration that can be safely modified without affecting other tests.
This function can be either used as a decorator similar to ``unittest.mock`` or as a context manager.

Test resources
..............

Test resources, like report files or case studies, can be stored in the ``tests/TEST_INPUTS`` directory.
This directory follows the same structure one would also use for the tool-suites installation environment.
The path to this directory can be accessed via the :attr:`~tests.helper_utils.TEST_INPUTS_DIR` attribute.
If using the :func:`~tests.helper_utils.replace_config()` wrapper or context manager without providing an own configuration, the relevant paths in the replaced configuration object are already pointed to this environment.
Keep the data put in this directory as small as possible to avoid bloating the repository.

.. warning::
    Make sure that your tests *do not write to this directory* to maintain an idempotent test environment.
    If you really need to write files, use `temporary directories` instead.

-----

Module: helper_utils
....................

.. automodule:: tests.helper_utils
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

Releasing VaRA-TS and VaRA related tools/libraries
..................................................

In general, all VaRA related tools and libraries with the same release should be compatible with each other, e.g., `vara-11.1.0` for vara-llvm-project needs to work with vara-tool-suite release `vara-11.1.0`.
We try to prevent breaking changes so that the tool suite works with many different VaRA versions, but sometimes breaking changes between releases are necessary.

Prepare release tooling
^^^^^^^^^^^^^^^^^^^^^^^

Before we can create a release, we need to install and prepare our release tools.

Install:

.. code-block:: console

    pip install --user wheel tox

Configure pypi credentials

.. code-block:: none

    [distutils]
      index-servers =
        testpypi
        pypi

    [pypi]
      repository = https://upload.pypi.org/legacy/
      username = __token__
      password = $PYPI_PASSWORD

    [testpypi]
      repository = https://test.pypi.org/legacy/
      username = __token__
      password = $PYPI_PASSWORD

vara-tool-suite
^^^^^^^^^^^^^^^

Ensure that all branches are in the correct state.

.. code-block:: console

    cd VaRA-Tool-Suite
    git checkout vara
    git pull
    git checkout vara-dev
    git pull

[Optional]: Update the version numbers, should a larger bump be needed.

.. code-block:: console

    git checkout vara-dev
    # Update varats/setup.py and varats-core/setup.py to the next version
    # Update varats/setup.py to depend on the new core version
    git commit -m "Bump version to $NEW_VERSION"
    git push origin vara-dev

Integrate the changes from develop into the release branch `vara`.

.. code-block:: console

    git checkout vara
    git merge vara-dev

Build and upload release files with tox and tag the new release, this automatically builds both namespace packages `varats` and `varats-core`.

.. code-block:: console

    tox -e release
    git tag -s vara-X.Y.Z

    git push origin vara
    git push origin vara-X.Y.Z

Prepare the next version, by default we assume a small bump.

.. code-block:: console

    git checkout vara-dev
    # Update varats/setup.py and varats-core/setup.py to the next version
    # Update varats/setup.py to depend on the new core version
    git commit -m "Bump version to $NEW_VERSION"
    git push origin vara-dev

vara-feature
^^^^^^^^^^^^

Ensure that all branches are in the correct state.

.. code-block:: console

    cd vara-feature
    git checkout vara
    git pull
    git checkout vara-dev
    git pull

[Optional]: Update the version numbers, should a larger bump be needed.

.. code-block:: console

    git checkout vara-dev
    # Update setup.py to the next version
    git commit --allow-empty -m "Bump version to $NEW_VERSION"
    git push origin vara-dev

Integrate the changes from develop into the release branch `vara`.

.. code-block:: console

    git checkout vara
    git merge vara-dev

Build and upload release files with tox and tag the new release.

.. code-block:: console

    tox -e release
    git tag -s vara-X.Y.Z

    git push origin vara
    git push origin vara-X.Y.Z

Prepare the next version.

.. code-block:: console

    git checkout vara-dev
    # Update setup.py to the next version
    git commit --allow-empty -m "Bump version to $NEW_VERSION"
    git push origin vara-dev

VaRA and vara-llvm-project
^^^^^^^^^^^^^^^^^^^^^^^^^^

Releasing
"""""""""

.. code-block:: console

    cd vara-llvm-project
    git checkout vara-$DEV_VERSION-dev
    git pull
    git checkout -b vara-$DEV_VERSION
    git push --set-upstream origin vara-$DEV_VERSION
    git tag -s vara-X.Y.Z
    git push origin vara-X.Y.Z

    cd vara
    git checkout vara-dev
    git pull
    git checkout vara
    git pull
    git merge vara-dev
    git tag -s vara-X.Y.Z
    git push
    git push origin vara-X.Y.Z

Preparing new development branches
""""""""""""""""""""""""""""""""""

Before upgrading to the new LLVM base check build and run tests.

.. code-block:: console

    cd vara-llvm-project
    git checkout vara-$DEV_VERSION-dev
    git checkout -b vara-$DEV_VERSION_NEXT-dev
    # fetch upstream llvm changes
    git fetch upstream
    git rebase --onto $NEXT_LLVM_RELEASE_BASE $PREV_LLVM_RELEASE_BASE vara-$DEV_VERSION_NEXT-dev
    # Fix regressions and API changes introduced by the new LLVM version.
    # Check if the phasar submodule needs an update.
    git push --set-upstream origin vara-$DEV_VERSION_NEXT-dev

Set the new development default in varats to $DEV_VERSION_NEXT.

.. code-block:: console

   cd vara-tools-suite
   vi varats-core/varats/utils/settings.py
   # Set vara:version to `XY` of $DEV_VERSION_NEXT
