vara-develop
============

This tool is a convenience tool for managing the **VaRA** git repositories.
This tool is also available as ``vd``.

.. program-output:: vara-develop -h
    :nostderr:

The subcommands ``vd checkout``, ``vd pull``, ``vd push`` and ``vd status``
work as their respective git counterparts, but operate on multiple repositories
at once.

.. program-output:: vara-develop status -h
    :nostderr:

The subcommand ``vd f-branches`` shows all feature branches of the vara
repositories.