vara-container
==============

This tool is used to manage the base container images used when using our :ref:`container support<Container Guide>`.

.. program-output:: vara-container -h
    :nostderr:

This tool provides an easy way to select the research tool that is used in the base containers:

.. program-output:: vara-container select -h
    :nostderr:

With `vara-container build`, you can build all base container images for the current research tool.
Additional flags allow to only re-build parts of the base image.

.. program-output:: vara-container build -h
    :nostderr:

Existing base images can also be deleted:

.. program-output:: vara-container delete -h
    :nostderr:

.. note::

  This command does not delete project and experiment images, it only deletes base images.
  To delete project and experiment images use BenchBuild's `benchbuild container rmi` command.
