vara-container
==============

This tool is used to manage the base container images used when :ref:`running benchbuild in container mode<Running BenchBuild in a container>`.

.. program-output:: vara-container -h
    :nostderr:

This tool provides an easy way to select the research tool that is used in the base containers:

.. program-output:: vara-container select -h
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


If you plan on running BenchBuild with container support on slurm, the following command helps you set up the correct environment:

.. program-output:: vara-container prepare-slurm -h
    :nostderr:


.. warning::
  This command changes the location where container images are built and stored in the BenchBuild config.
  That means that all subsequent container images will reside in that directory including the base images that are built by this command.
  This also means, that the ``--node_dir`` option you pass to this command must be a path that can be created on both, the machine where this command is executed and on the slurm nodes.
  In general, it is a good idea to use some subdirectory of ``/tmp`` here, although that means that images and containers may be lost after a reboot.
