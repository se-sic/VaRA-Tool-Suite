vara-cs-gui
===========

This gui tool provides some functionality to create :ref:`case studies<Module: case_study>`.
Detailed information about how case studies work can be found :ref:`here<How to use case studies>`.

The gui is started by::

        vara-cs-gui

The gui provides 3 Strategies to generate case studies:
    - Manual revision selection: Select revision from the revision history of a project. Multiple revisions can be selected by holding `ctrl` and ranges by holding `shift`. Revisions which are blocked because of bugs in the compilation of the project are marked blue.
    .. figure:: vara-cs-gui-manual.png

    - Random Sampling: Sample a number of revisions using a random a Normal or HalfNormal Distribution.

    .. figure:: vara-cs-gui-sample.png

    - Sampling by Year: Sample a number of revisions per Year using a NormalDistribution.

    .. figure:: vara-cs-gui-yearly.png

The command line tool :ref:`vara-cs gen<vara-cs gen>` provides additional functionality.
