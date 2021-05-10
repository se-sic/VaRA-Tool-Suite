vara-container
==============

This tool is used to manage the base container images used when :ref:`running benchbuild in container mode<Running BenchBuild in a container>`.

.. program-output:: vara-container -h
    :nostderr:

This tool provides an easy way to select the research tool that is used in the base containers:

.. program-output:: vara-container select-tool -h
    :nostderr:

With `vara-container build`, you can build all base container images for the current research tool:

.. program-output:: vara-container build -h
    :nostderr:

Existing base images can also be deleted:

.. program-output:: vara-container delete -h
    :nostderr:

.. note::

  This command does not delete project and experiment images, it only deletes base images.
  To delete project and experiment images use BenchBuild's `benchbuild container rmi` command.
