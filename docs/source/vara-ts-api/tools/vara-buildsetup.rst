vara-buildsetup
===============

This tool manages your **VaRA** installation.

.. program-output:: vara-buildsetup -h
    :nostderr:

For a clean :ref:`setup<How to setup VaRA>`, you would typically first
initialize VaRA with::

    vara-buildsetup -i

and then trigger the build process with::

    vara-buildsetup -b

You can upgrade VaRA to a new version with::

    vara-buildsetup -u

If you want to upgrade to a specific release, use the ``--version`` flag::

    vara-buildsetup -u --version release_90

Don't forget to re-build VaRA after an upgrade!
