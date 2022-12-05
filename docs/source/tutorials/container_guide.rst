Container Guide
===============

VaRA-TS supports running experiments inside containers to make them more portable and reproducible.
This guide walks you through the steps how to prepare and execute experiments in containers and assumes that your system has already been set up for executing containers.
You can find the instructions for setting up containers on your system :ref:`here <Running BenchBuild in a Container>`.
More details about the inner workings of the container support in VaRA-TS can be found :ref:`here <Container support>`.
Note that, by default, the most recent version of VaRA-TS available from PyPI will be used inside the container.
If you want to use your local development version of VaRA-TS instead, you have to specify this in the ``.varats.yml`` configuration file by setting the value of ``from_source`` to true and the value of ``varats_source`` to the directory containing the source code of the VaRA-TS.

1. Preparing the research tool

   If the experiment you want to run makes use of a :ref:`research tool <Provided research tools>`, you have to build it specifically for each :ref:`base image <Using containers>` that is used by one of the projects you run your experiments on.
   This can be done by passing the ``--container=<base_container>`` flag when building the research tool, e.g.:

   .. code-block:: console

       vara-buildsetup build vara --container=DEBIAN_10

   Note that the underlying tools do not support network file systems. In the ``.benchbuild.yml`` configuration, you need to set the values of ``root`` and ``runroot`` to a directory that is locally available on the current machine. For example, you can use the following values:

   .. code-block:: yaml

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

3. Running the experiments

   Running your experiments inside a container is now as simple as passing an additional flag to ``vara-run``:

   .. code-block:: console

       vara-run -E JustCompile --container

   Do not forget to run

   .. code-block:: console

       vara-gen-bbconfig

   and to adapt the values as described in step 1 before running your experiments.
