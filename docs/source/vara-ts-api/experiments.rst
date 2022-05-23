Experiments
===========

``Experiments`` are the base concept how the tool suite and BenchBuild execute research experiments, e.g., measuring performance or analyzing a software project.
They are designed to make the execution of research experiments easy and reproducable by separating experiment specific steps from project specific ones.
For example, how a specific project is compiled is the responsibility of the project writer, where how the project is evaluated during a research experiment is the ``Experiment``'s task.

.. note::
  Details on how to run experiments can be found :ref:`here<Running experiments with BenchBuild>`.

How to add a new experiment to VaRA-TS
--------------------------------------
Designing a new ``Experiment`` is also quite simple.

* First, create a new python module in the ``experiments`` directory and add an experiment class which inherits from ``benchbuild.experiment.Experiment``.
  If VaRA-TS should provide automatic support for analyzing different versions, i.e., different revisions of a git based project, use :class:`~varats.experiment.experiment_util.VersionExperiment` as base class.
* Second, define two static variables for your experiment: ``NAME`` and ``REPORT_SPEC``
* Third, your experiment needs to pass an additional ``shorthand`` parameter.
* Next, override the ``actions_for_project`` method.
  This method should assign run-time/compile-time extensions and specify the list of actions that should be performed.
  Each action the experiment does is called a ``Step`` and will be executed by BenchBuild in order.
* Last, add your experiment for testing to the BenchBuild config file `vara-root/benchbuild/.benchbuild.yml` under plugins/experiments/value. After testing, integrate them into the tool suite by adding it to the experiment list in ``varats.tools.bb_config.generate_benchbuild_config``, so it will be automatically added to the BenchBuild config in the future.

.. note::
  For more information about ``Experiment``'s consider reading the BenchBuild `docs <https://pprof-study.readthedocs.io/en/master/>`_.

If you're looking for a simple example experiment, consider taking a look at :class:`~varats.experiments.just_compile.JustCompileReport`.

* :ref:`Tool suite provided experiments`
* :ref:`experiment utilities`

Tool suite provided experiments
-------------------------------

.. toctree::
   :maxdepth: 1

   experiments/just_compile
   experiments/blame_report_experiments
   experiments/szz

Experiment utilities
--------------------

WLLVM module
............

.. automodule:: varats.experiment.wllvm
    :members:
    :undoc-members:
    :show-inheritance:

------

Experiment utilities module
...........................

.. automodule:: varats.experiment.experiment_util
    :noindex:
    :members:
    :undoc-members:
    :show-inheritance:
