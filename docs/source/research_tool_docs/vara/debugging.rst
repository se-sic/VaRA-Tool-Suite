*********
Debugging
*********

A quick guide on how to test and debug VaRA.

Running VaRA tests
==================

VaRA comes with many regression tests to ensure the analyses and extraction is working correctly.
Furthermore, VaRA regression tests also contain tests for the extensions vara-clang and vara-llvm.

To run all tests:

.. code-block:: bash

  make check-vara

To run all unittests in ``unittests``:

.. code-block:: bash

  make check-vara-unittests

To run all clang related regression tests in ``test/vara-clang/``:

.. code-block:: bash

  make check-vara-clang

To run all llvm related regression tests in ``test/vara-llvm/``:

.. code-block:: bash

  make check-vara-llvm

Testing commit and git analyses
-------------------------------

For testing of commit and git related analyses, VaRA offers additional testing repositories which are automatically provided to your regression or unittests.

For unittests, just include the ``UnittestHelper.h`` and load a repository by specifying its subpath, relative to the ``TestRepositories`` folder.

.. code-block:: cpp

    #include "UnittestHelper.h"

    std::string TestRepoPath = getTestRepositoryBase("BasicTestRepos/ExampleRepo/"));
    VaRAContext &VC = VaRAContext::getContext();
    Repository &Repo = VC.addRepository(getTestRepositoryBase(TestRepoPath));

For regression tests, the same subpath can be added to the test-repo meta-variable ``%test_repos/``, which allows the test to refer to either a repository or a file inside a repository.

.. code-block:: llvm

  ; RUN: %clang ... %test_repos/BasicTestRepos/ExampleRepo/main.c ...
  ; RUN: %opt ... %test_repos/BasicTestRepos/ExampleRepo/ ...


Debugging options
=================
VaRA can produce specific debug output to ease debugging. To enable this output use LLVM debugging options.
Add the corresponding debug flag to your run line ``-debug-only=$DB_FLAG``

VaRA specific DB_FLAGs

* FD  => ``FeatureDetection`` debug info
* FD+ => ``FeatureDetection`` extra debug info
