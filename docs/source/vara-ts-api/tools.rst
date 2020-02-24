Tools
=====

`TODO (se-passau/VaRA#576) <https://github.com/se-passau/VaRA/issues/576>`_: write docs

Tools overview
--------------
* :ref:`vara-art`
* :ref:`vara-plot`

vara-art
*********

This tool manages the :ref:`Artefacts<Module: artefacts>` of a
:ref:`paper config<How to use paper configs>`.

.. program-output:: vara-art -h

The subcommand ``vara-art add`` adds a new artefact to the current paper config.

.. program-output:: vara-art add -h

For example, an artefact that will generate a ``paper_config_overview_plot``
(see :ref:`plots<Module: plots>`) for the current paper config can be added
via::

    vara-art add plot "overview plot" report_type=EmptyReport plot_type=paper_config_overview_plot

.. note::

    The double quotes around the artefact name are only needed if the name
    contains spaces or other characters with special meaning.

.. _vara-art-generate:

To generate all artefacts of the current paper-config, use::

    vara-art generate

If you only want to generate some specific artefacts, you can specify their
names with the ``--only`` parameter::

    vara-art generate --only "overview plot"

You can list all artefacts of the current paper config with::

    vara-art list

To show details for one or more artefacts, use::

    vara-art show "overview plot"

You can give multiple artefact names to ``vara-art show`` to see details for
multiple artefacts at once.


vara-plot
.........

TODO: add example


vara-cs
.......
TODO: add example

vara-cs ext
***********

vara-cs status
**************
