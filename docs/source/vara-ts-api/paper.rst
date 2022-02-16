Paper and case study handling
=============================

Whenever we design experiments that look at specific revisions of a project, we run into the problem that to re-evaluate our experiment data, we need to preserve the set of revisions.
Exactly for this problem, the tool suite provides case studies that preserve the information about which revision of a project was analyzed.
In addition, to fully preserve also the set of projects that were analyzed, we designed paper configs as a collection of different case studies.
Furthermore, we can use paper configs and case studies not only to re-evaluate our own experiment, but we also allow others to reproduce our data or design their own experiment based on our project and revision selection.

How to use case studies
-----------------------
If one wants to analyze a particular set of revisions or wants to re-evaluate the same revision over and over again, we can fixate the revisions we are interested in by creating a :class:`CaseStudy`.
First, create a folder, where your config should be saved.
Then, create a case study that specifies the revision to be analyzed.
To ease the creation of case studies the tool suite offers different selection strategies to choose revisions from the projects history, e.g., based on a probability distribution.

For example, to get the latest revision of a project use:

    vara-cs gen -p PROJECT_NAME select_latest

As another example, we can generate a new case study for the project ``gzip``, drawing 10 revision from the projects history based on a half-normal distribution, with::

    vara-cs gen -p gzip select_sample HalfNormalSamplingMethod --num-rev 10

Multiple case studies, e.g., a set of case studies used for a paper, can be grouped into a *paper config* so that they can be managed together more easily.
For more information see :ref:`How to use paper configs`.

Extending an existing case study is easy, just select more revisions and they will be added automatically.
Should you wish to drop the old revisions, just pass `--override`, this will remove the old ones and afterwards add the newly selected revisions.

.. warning::

    The specified distribution only relates to the newly added revisions but does not include revisions previously added.
    If one wants to draw all revision according to the same distribution the old case study needs to be overwritten.


How to use paper configs
------------------------

Paper configs are used to group different case studies together.
Take, for example, the case where one wants to analyze the projects, gzip and git, for the evaluation of a paper that get's submitted to `ase-17`.
First, one creates different case studies for each project selecting the different revisions that should be analyzed.
Second, all case studies related to the evaluation for `ase-17` are grouped into a folder -- the paper config -- to relate them to the paper.
Now we can design and run our experiment for `ase-17` on all revisions added through case studies in the paper config and generate our experiment results.

The paper config now allows us to reproduce all the results for our paper with a single call to the tool suite.
Furthermore, this is also helpful for other researchers that are now able to reproduce our results.

In more detail, our specified paper config allows the tool suite to tell BenchBuild which revisions should be analyzed to evaluate a set of case studies.
For example, a setup could look like this::

    paper_configs
        ├── ase-17
        │       ├── gzip_0.case_study
        │       ├── gzip_1.case_study
        │       └── git_0.case_study
        └── icse-18
                ├── gzip_0.case_study
                └── git_0.case_study

In this example, we got two paper configs, one for ``ase-17`` another for ``icse-18``.
We see different case studies for ``gzip`` and ``git``, notice here that we can create multiple case studies for one project.
If we now want to evaluate our set for ``icse-18`` we set the paper-config folder to the root of our config tree and select the ``icse-18`` folder as our current config in the settings file ``.vara.yaml``, like this::

    paper_config:
    current_config:
        value: icse-18
    folder:
        value: /home/foo/vara/paper_configs/

Next, we can run our experiment with BenchBuild as usual. During experiment execution, BenchBuild will load our config and only evaluate the needed revisions.

The current status of all case studies belonging to the current paper config, can be visualized with :ref:`vara-cs status`::

    >>> vara-cs status -s $EXPERIMENT_NAME
    CS: gzip_0: (0/5) processed
    CS: gzip_1: (2/5) processed
    CS: gzip_2: (5/5) processed
    CS: libvpx_0: (0/5) processed

The tool :ref:`vara-pc` provides a simple command line interface for creating
and managing paper configs.

Artefacts
.........

The :ref:`artefacts module<Module: artefacts>` provides an easy way to attach
descriptions of artefacts, like plots or result tables, to a paper config.
This way, reproducing the exact same plots for a paper config over and over
again becomes as easy as invoking :ref:`a single command<vara-art-generate>`.

For more information about how to create and manage artefacts, refer to the
documentation of the :ref:`vara-art` tool.


Paper and case study modules
----------------------------
* :ref:`Module: paper_config`
* :ref:`Module: case_study`
* :ref:`Module: artefacts`
* :ref:`Module: paper_config_manager`

Module: paper_config
....................

.. automodule:: varats.paper_mgmt.paper_config
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

Module: artefacts
..................

.. automodule:: varats.paper_mgmt.artefacts
    :members:
    :undoc-members:
    :show-inheritance:

-----

Module: paper_config_manager
............................

.. automodule:: varats.paper_mgmt.paper_config_manager
    :members:
    :undoc-members:
    :show-inheritance:
