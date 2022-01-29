vara-buildsetup
===============

This tool manages your research tool installations.

.. program-output:: vara-buildsetup -h
    :nostderr:

The buildsetup tool allows you to initialize different research tools that are included an managed with the tool suite in the same manner.
For example, see below how one would initialize and build **VaRA**.

For a clean :ref:`setup<How to setup VaRA>`, you would typically first
initialize VaRA with::

    vara-buildsetup init vara

and then trigger the build process with::

    vara-buildsetup build vara

You can upgrade VaRA to a new version with::

    vara-buildsetup update vara

If you want to upgrade to a specific release, use the ``--version`` flag::

    vara-buildsetup update vara --version release_100

Don't forget to re-build VaRA after an upgrade!
