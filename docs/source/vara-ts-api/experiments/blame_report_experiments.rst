Experiment: GenerateBlameReport
===============================

Different experiments to generate blame reports.

.. tip::

  If you want to run the same project + version multiple times via slurm you need to empty the ``$VARATS_ROOT/benchbuild/BC_files`` directory in between runs because the path to the git repository will change. See `#494 <https://github.com/se-sic/VaRA/issues/494>`_

.. tip::

  To use interaction filters, we recommend storing all of them in a separate directory (e.g., ``$VARATS_ROOT/benchbuild/interaction_filters``) with descriptive names and symlinking them to the place where the experiment expects them.

Module: BlameReportExperiment
-----------------------------

.. automodule:: varats.experiments.vara.blame_report_experiment
    :members:
    :undoc-members:
    :show-inheritance:

------

Module: BlameExperiment
-----------------------

.. automodule:: varats.experiments.vara.blame_experiment
    :members:
    :undoc-members:
    :show-inheritance:
