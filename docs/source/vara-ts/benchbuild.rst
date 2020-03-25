Running experiments with BenchBuild
===================================

VaRA-TS provides different preconfigured experiments and projects.
In order to execute an experiment on a project we use `BenchBuild <https://github.com/PolyJIT/benchbuild>`_, an empirical-research toolkit.

Setup: Configuring BenchBuild
-----------------------------
First, we need to generate a folder with a configuration file for BenchBuild in the vara root directory. This is done with:

.. code-block:: bash

  vara-gen-bbconfig

Running BenchBuild experiments
----------------------------------
Second, we change into the benchbuild folder and run an experiment that generates `BlameReports` for provided projects. In this case we use `gzip`.

.. code-block:: bash

  cd $VARA_ROOT/benchbuild
  benchbuild -vv run -E GenerateBlameReport gzip

The generated result files are place in the ``vara/results/$PROJECT_NAME`` folder and can be further visualized with VaRA-TS graph generators.
