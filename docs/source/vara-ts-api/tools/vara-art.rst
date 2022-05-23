vara-art
========

This tool manages the :ref:`Artefacts<Module: artefacts>` of a
:ref:`paper config<How to use paper configs>`.

.. program-output:: vara-art -h
    :nostderr:

.. _vara-art-generate:

To generate all artefacts of the current paper-config, use::

    vara-art generate

If you only want to generate some specific artefacts, you can specify their
names with the ``--only`` parameter::

    vara-art generate --only "PC Overview"

You can list all artefacts of the current paper config with::

    vara-art list

To show details for one or more artefacts, use::

    vara-art show "PC Overview"

You can give multiple artefact names to ``vara-art show`` to see details for
multiple artefacts at once.
