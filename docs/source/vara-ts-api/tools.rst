Tools
=====

`TODO (se-passau/VaRA#576) <https://github.com/se-passau/VaRA/issues/576>`_: write docs

Tools overview
--------------
* :ref:`vara-art`
* :ref:`vara-plot`

vara-art
*********

This tool manages the :ref:`Artefacts<Module: artefacts>` of a paper config.

.. program-output:: vara-art -h

The subcommand ``vara-art add`` adds a new artefact to the current paper config.

.. program-output:: vara-art add -h

For example, an artefact that will generate a ``paper_config_overview_plot``
for the current paper config (see :ref:`plots<Module: plots>`) can be added via:

.. code-block:: bash

    vara-art add plot overview2 report_type=EmptyReport plot_type=paper_config_overview_plot

To generate all artefacts of the current paper-config, use

.. code-block:: bash

    vara-art generate

vara-plot
*********

TODO: add example
