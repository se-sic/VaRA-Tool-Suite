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

.. TODO: rewrite once we have a better vara-cs gen/ext tool

.. code-block:: bash

    vara-cs gen paper_configs/tutorial/ HalfNormalSamplingMethod -p xz --num-rev 10

This creates a new case study for the project xz and includes 10 revisions sampled with a half normal distribution.

Run an Experiment
-----------------

Now that we have a paper config and a case study set up, we can run experiments on them.
An experiment is a set of tasks that should be executed for each version of the projects as specified in the case studies of the current paper config.
In this tutorial, we run an experiment that simply compiles the project.
For more information on experiments in VaRA-TS and a list of available experiments see :ref:`here <Experiments>`.
Under the hood, the execution of experiments is handled by `BenchBuild <https://github.com/PolyJIT/benchbuild>`_, an empirical-research toolkit, but VaRA-TS provides a tool :ref:`vara-run` to easily run experiments for all case studies in a paper config.

.. code-block:: bash

  vara-run -E JustCompile

Since the ``JustCompile`` experiment produces ``EmptyReports``, we can view the status of the experiment runs as such.

.. code-block:: bash

  vara-cs -s EmptyReport
