Paper and case study handling
=============================

`TODO (se-passau/VaRA#573) <https://github.com/se-passau/VaRA/issues/573>`_: write docs

How to use case studies
-----------------------
If one wants to analyze a particular set of revisions or wants to reevaluate the same revision over and over again, we can fix the analyzed revisions by creating a :class:`CaseStudy`. First, create a folder, where your config should be saved. Then, create a case study that fixes the revision to be analyzed. In order to ease the creation of case studies VaRA-TS offers different sampling methods to choose revisions from the projects history based on a probability distribution.

For example, we can generate a new case study for ``gzip``, drawing 10 revision from the projects history based on a half-normal distribution, with::

    vara-cs gen PATH_TO_PAPER_CONF_DIR/ half_norm PATH_TO_REPO/ --num-rev 10

Created case studies should be grouped into folders, e.g., a set of case studies used for a paper, called paper config.
For more information see :ref:`How to use paper configs`.

Extending case studies
......................
Case studies group together revisions but sometimes these groups need to be changed or extended, e.g., when we want so sample a few more revisions to gather data for a specific revision range. To simplify that, our tool suite provides :ref:`vara-cs ext`, a tool for extending and changing case studies.

For example::

    vara-cs ext paper_configs/ase-17/gzip_0.case_study distrib_add gzip/ --distribution uniform --num-rev 5

will add 5 new revision, sampled uniformly, to the case study.

In more detail, case studies have different stages that are separated from each other. This allows us to for example extend a case study with an specific revision without changing the initial set of revisions, e.g., stage 0.

For example::

    vara-cs ext paper_configs/ase-17/gzip_0.case_study simple_add gzip/ --extra-revs 0dd8313ea7bce --merge-stage 3

will add revision ``0dd8313ea7bce`` to the stage 3 of the gzip case study, allowing us to analyze it and draw different plots, e.g., one containing only stage 0 data and another with all stages included

How to use paper configs
------------------------
`TODO (se-passau/VaRA#573) <https://github.com/se-passau/VaRA/issues/573>`_: write docs


This allows the tool suite to tell BenchBuild which revisions should be analyzed to evaluate a set of case studies for a paper. For example, a setup could look like::

    paper_configs
        ├── ase-17
        │       ├── gzip_0.case_study
        │       ├── gzip_1.case_study
        │       └── git_0.case_study
        └── icse-18
                ├── gzip_0.case_study
                └── git_0.case_study

In this example, we got two paper configs, one for ``ase-17`` another for ``icse-18``. We see different case studies for ``gzip`` and ``git``, notice here that we can create multiple case studies for one project. If we now want to evaluate our set for ``icse-18`` we set the paper-config folder to the root of our config tree and select the ``icse-18`` folder as our current config, like this::

    paper_config:
    current_config:
        value: icse-18
    folder:
        value: /home/foo/vara/paper_configs/

Next, we can run our experiment with BenchBuild as usual. During experiment execution BenchBuild will load our config and only evaluate the needed revisions.

The current status of a case study can be visualized with :ref:`vara-cs status`::

    >>> vara-cs status -s
    CS: gzip_0: (0/5) processed
    CS: gzip_1: (2/5) processed
    CS: gzip_2: (5/5) processed
    CS: libvpx_0: (0/5) processed

Paper and case study modules
----------------------------
* :ref:`Module: paper_config`
* :ref:`Module: case_study`
* :ref:`Module: paper_config_manager`

Module: paper_config
....................

.. automodule:: varats.paper.paper_config
    :members:
    :undoc-members:
    :show-inheritance:

-----

Module: case_study
..................

.. automodule:: varats.paper.case_study
    :members:
    :undoc-members:
    :show-inheritance:

-----

Module: paper_config_manager
............................

.. automodule:: varats.paper.paper_config_manager
    :members:
    :undoc-members:
    :show-inheritance:
