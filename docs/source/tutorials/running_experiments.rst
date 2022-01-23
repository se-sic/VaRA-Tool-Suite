Running Experiments
===================

A goal of VaRA-TS is to make experiments easily reproducible.
Therefore, we have the concept of `paper configs`.
Basically, a paper config is a collection of `case studies`.
Each case study specifies what revisions and configurations of a project need to be analyzed.
You can find more details about paper configs and case studies :ref:`here <Paper and case study handling>` and an overview of the whole VaRA-TS pipeline :ref:`here <Tool-Suite Pipeline Overview>`.

Creating a Paper Config
-----------------------

That means before we can run any experiments, we first need to create a paper config.
Paper configs can be managed with the :ref:`vara-pc` tool.

.. code-block:: bash

  # create a new paper config named 'tutorial'
  vara-pc create tutorial

The new paper config resides as a folder ``tutorial`` in ``varats-root/paper_configs/``
When running ``vara-pc list``, the star next to the name of our paper config confirms that the paper config is selected.
All commands creating or modifying any case studies always apply to the currently selected paper config.
We can select a different paper config with ``vara-pc select``.

Creating a Case Study
---------------------

Next, we need to populate the paper config with a case study.
Case studies are managed with the :ref:`vara-cs` tool.

For example, we can for example select revision `e7da44d515` from the project `xz` like this:

.. code-block:: bash

    vara-cs gen -p xz select_specific e7da44d515

or to select the lastest revision of xz like this:

.. code-block:: bash

    vara-cs gen -p xz select_latest

This creates a new case study for the project xz and including the selected revisions.

Run an Experiment
-----------------

Now that we have a paper config and a case study set up, we can run experiments on them.
An experiment is a set of tasks that should be executed for each version of the projects as specified in the case studies of the current paper config.
In this tutorial, we run an experiment that simply compiles the project.
For more information on experiments in VaRA-TS and a list of available experiments see :ref:`here <Experiments>`.
Under the hood, the execution of experiments is handled by `BenchBuild <https://github.com/PolyJIT/benchbuild>`_, an empirical-research toolkit, but VaRA-TS provides a tool :ref:`vara-run` to easily run experiments for all case studies in a paper config.

.. code-block:: bash

  vara-run -E JustCompile

To visualize which revisions have already been processed, we use again the :ref:`vara-cs` tool but this time we query with `status`.

.. code-block:: bash

  vara-cs status JustCompile
