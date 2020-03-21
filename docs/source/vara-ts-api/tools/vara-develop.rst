vara-develop
============

This tool is a convenience tool for managing the git repositories of different research tools.
This tool is also available as ``vd``.

.. program-output:: vara-develop -h
    :nostderr:

Take for example, the subcommands ``vd vara checkout``, ``vd vara pull``, ``vd vara push`` and ``vd vara status`` work as their respective git counterparts, but operate on multiple repositories at once.
We use ``vara`` here as an example for a research project but the commands work on all research projects.

.. program-output:: vara-develop vara status -h
    :nostderr:

The subcommand ``vd vara f-branches`` shows all feature branches of the vara
repositories.
