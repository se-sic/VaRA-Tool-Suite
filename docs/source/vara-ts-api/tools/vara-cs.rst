vara-cs
=======

This tool provides functionality to create and manage
:ref:`case studies<Module: case_study>`.
Detailed information about how case studies work can be found :ref:`here<How to use case studies>`.

The `vara-cs` tool has various sub-commands which we explain in more detail
below:

.. program-output:: vara-cs -h
    :nostderr:


vara-cs gen
-----------

The ``vara-cs gen`` command generates a new case study.
You can chose what paper config the case study should belong to
and what project or project revisions are part of the case study
via command line parameters:

.. program-output:: vara-cs gen -h
    :nostderr:


vara-cs ext
-----------

The ``vara-cs ext`` command adds additional revisions to an existing case study.

The chosen *extender strategy* determines how the additional revisions are
selected:

- :func:`simple_add<varats.paper.case_study.extend_with_extra_revs>`:
  adds the revisions given via ``--extra-revs``
- :func:`distrib_add<varats.paper.case_study.extend_with_distrib_sampling>`:
  samples ``num-rev`` revisions with the given ``distribution`` from the case
  study's project
- :func:`smooth_plot<varats.paper.case_study.extend_with_smooth_revs>`:
  selects new revisions based on the steepness of a graph
  (given via ``--plot-type``) and the given ``boundary-gradient``
- :func:`per_year_add<varats.paper.case_study.extend_with_revs_per_year>`:
  adds ``num-rev`` random revisions from each year in the case study's project's
  history
- :func:`release_add<varats.paper.case_study.extend_with_release_revs>`:
  adds all release revisions from the case study's project

.. program-output:: vara-cs ext -h
    :nostderr:


vara-cs status
--------------

The ``vara-cs status`` command prints status information about the results
of your experiments.
It can give an overview over the status of all case studies or more detailed
information about specific case studies.

.. program-output:: vara-cs status -h
    :nostderr:


vara-cs package
---------------

The ``vara-cs package`` command allows to package all files belonging to the
current paper config into a ``.zip`` file.

.. program-output:: vara-cs package -h
    :nostderr:


vara-cs view
---------------

The ``vara-cs view`` command allows to easily open result files in your favourite editor.
The tool searches for result files matching the given commit hash and presents you a list with the found files.
The selected file then gets opened using the program in your ``EDITOR`` environment variable.

.. program-output:: vara-cs view -h
    :nostderr:
