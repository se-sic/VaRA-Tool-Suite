Container Guide
===============

VaRA-TS supports running experiments inside containers to make them more portable and reproducible.
This guide walks you through the steps how to prepare and execute experiments in containers and assumes that your system has already been set up for executing containers.
For additional resources, see the following pages:

- :ref:`Running BenchBuild in a Container` explains how to initially set up containers on your system and how they work with BenchBuild under the hood.
- :ref:`Container support` explains how VaRA-TS creates and manages reusable base images that can be used by projects.
- :ref:`vara-container` is the tool that is used for managing these base images.
- :ref:`Using Containers` explains how container support can be implemented for a project.
- :ref:`Slurm and Container` demonstrates the container support integration with slurm.



Note that, by default, the most recent version of VaRA-TS available from PyPI will be used inside the container.
If you want to use your local development version of VaRA-TS instead, you have to specify this in the ``.varats.yml`` configuration file by setting the value of ``from_source`` to true and the value of ``varats_source`` to the directory containing the source code of the VaRA-TS.

1. Preparing the research tool

   If the experiment you want to run makes use of a :ref:`research tool <Provided research tools>`, you have to build it specifically for each :ref:`base image <Using containers>` that is used by one of the projects you run your experiments on.
   This can be done by passing the ``--container=<base_container>`` flag when building the research tool, e.g.:

   .. code-block:: console

       vara-buildsetup build vara --container=DEBIAN_10

   Note that the underlying tools may not support network file systems (i.e., if you are using podman in `rootless mode <https://github.com/containers/podman/blob/master/rootless.md>`_).
   In the ``.benchbuild.yml`` configuration, you need to set the values of ``container/root`` and ``container/runroot`` to a directory that is locally available on the current machine.
   For example, you can use the following values:

   .. code-block:: yaml

        container:
            root:
                default: !create-if-needed '/scratch/<username>/vara-root/benchbuild/containers/lib'
                desc: Permanent storage for container images
                value: !create-if-needed '/local/storage/<username>/benchbuild/containers/lib'
            runroot:
                default: !create-if-needed '/scratch/<username>/vara-root/benchbuild/containers/run'
                desc: Runtime storage for containers
                value: !create-if-needed '/local/storage/<username>/benchbuild/containers/run'


2. Building the base images

   The next step is to prepare the base images.
   This is done with the :ref:`vara-container` tool.
   If your experiments use a research tool, you have to tell the tool suite to include it in the base images like this:

   .. code-block:: console

       vara-container select -t vara

   Now you can create the base images:

   .. code-block:: console

       vara-container build

   You can use the flag ``-i <base_image>`` to only build a specific base image and should add ``--export`` if you want to use the image with slurm.
   There are also flags for re-building only parts of an image, e.g., to just update the tool suite.
   These flags can drastically remove the time it takes to build an image.

3. Running the experiments

   Running your experiments inside a container is now as simple as passing an additional flag to ``vara-run``:

   .. code-block:: console

       vara-run -E JustCompile --container
