Running experiments with BenchBuild
===================================

VaRA-TS provides different preconfigured experiments and projects.
In order to execute an experiment on a project we use `BenchBuild <https://github.com/PolyJIT/benchbuild>`_, an empirical-research toolkit.

Setup: Configuring BenchBuild
-----------------------------
First, we need to generate a folder with a configuration file for BenchBuild in the vara root directory. This is done with:

.. code-block:: bash

  vara-gen-bbconfig

Running BenchBuild experiments
------------------------------
Second, we change into the benchbuild folder and run an experiment that generates `BlameReports` for provided projects. In this case we use `gzip`.

.. code-block:: bash

  cd $VARA_ROOT/benchbuild
  benchbuild -vv run -E GenerateBlameReport gzip

The generated result files are place in the ``vara/results/$PROJECT_NAME`` folder and can be further visualized with VaRA-TS graph generators.

Running BenchBuild outside the ``$VARA_ROOT/benchbuild`` directory
------------------------------------------------------------------
To execute BenchBuild from another directory the ``VARA_ROOT`` environment variable must be set, so varats and benchbuild can locate the varats configuration file.

.. code-block:: bash

  # temporary:
  export VARA_ROOT=/path/to/your/vara/root/directory
  # permanent:
  echo 'export VARA_ROOT=/path/to/your/vara/root/directory' >> ~/.$(basename $0)rc

How-to configure BenchBuild yourself
------------------------------------
BenchBuild's configuration file ``.benchbuild.yml`` normally is placed inside the ``benchbuild`` folder, which is located in the vara root folder.
A default version of this file can be automatically generated with our tool :ref:`vara-gen-bbconfig`.
To adapt and tune BenchBuild further, you can moify the different configuration flags in this config file. The following list shows the most important ones:

* Adding extra paths to the environment

.. code-block:: yaml

  env:
    path:
      value: ["paths from your system that should be included in the PATH variable for experiments"]

* Other experiments or projects can be loaded similar to python imports

.. code-block:: yaml

  plugins:
  experiments:
    default:
      - varats.vara-experiments.CommitAnnotationReport
      - varats.vara-experiments.RegionAnalyser
  projects:
    default:
      - varats.vara-projects.git.gzip
      - pythonmodule.projectclass

* Enable/Disable BenchBuild version support, i.e., let BB consider all revisions from a project or just the latest one.

.. code-block:: yaml

  versions:
    full:
      default: false
      desc: Ignore default sampling and provide full version exploration.
      value: true

* Adapt the number of threads that should be used for project compilation.

.. code-block:: yaml

  jobs:
    desc: Number of jobs that can be used for building and running.
    value: '4'

* Adapt the number of parallel running experiment executions.

.. code-block:: yaml

  parallel_processes:
    desc: Proccesses use to work on execution plans.
    value: 4

Running BenchBuild in a Container
---------------------------------

BenchBuild can run its experiments inside a container.
This allows to customize the execution environment on a per-project(-version) and per-experiment level.

Configuring the Container Support
.................................

To use BenchBuild's container support, you first need to setup `buildah <https://github.com/containers/buildah/blob/master/install.md>`_ and `podman <https://podman.io/getting-started/installation>`_ on your system.
Please follow their install instructions on how to setup both tools.
We highly recommend to use buildah and podman in rootless mode.
Keep in mind that you have to set a subuid and subgid mapping on all machines that need to run containers.
You also need to install `crun` on those machines.
For debian, this can be don with the following command::

    sudo apt install crun

Then, make sure that the following parameters in the :ref:`BenchBuild config <How-to configure BenchBuild yourself>` are set.
If you generated your configuration via :ref:`vara-gen-bbconfig`, these options were automatically set.

.. code-block:: yaml

  container:
    from_source:
      desc: Install BenchBuild from source or from pip (default)
      value: false
    mounts:
        desc: List of paths that will be mounted inside the container.
        value:
        - [<path-to-varats-root>/results, /varats_root/results]
        - [<path-to-varats-root>/benchbuild/BC_files, /varats_root/BC_files]
        - [<path-to-varats-root>/vara/paper_configs, /varats_root/paper_configs]
    root:
        desc: Permanent storage for container images
        value: !create-if-needed '<path-to-varats-root>/containers/lib'
    runroot:
        desc: Runtime storage for containers
        value: !create-if-needed '<path-to-varats-root>/containers/run'
    runtime:
        desc: Default container runtime used by podman
        value: /usr/bin/crun
    source:
        desc: Path to benchbuild's source directory
        value: '</path/to/benchbuild>'


Executing Experiments in a Container
....................................

If your experiment makes use of a ref:`research tool`, the next step is to select the correct research tool for your experiment.
Afterwards, you need to build the base containers.
Both tasks can be accomplished using the :ref:`vara-container` tool.
Remember to first select a research tool and then build the base containers afterwards.

You can now run your experiments in a container simply by replacing the ``run`` in your BenchBuild command with ``container``, for example, like this:

.. code-block:: bash

  cd $VARA_ROOT/benchbuild
  benchbuild -vv container -E GenerateBlameReport gzip

Note, that each project is responsible for providing a :ref:`base container image <Using Containers>` to run in.

.. warning::

  BenchBuild configuration values are not automatically propagated into the container.
  If a specific value is needed either the base image needs to provide it or the project/experiment needs to add the specific BenchBuild environment variable to its layer.

Using buildah and podman on the Commandline
...........................................

For more advanced users, it might be useful to work with buildah and podman directly from the commandline, e.g., when debugging container images.
In these situations, it can come in handy to create some shell aliases that set the correct `root` and `runroot` to for the buildah and podman commands::

    alias bbuildah='buildah --root <path-to-varats-root>/containers/lib --runroot <path-to-varats-root>/containers/run'
    alias bpodman='podman --root <path-to-varats-root>/containers/lib --runroot <path-to-varats-root>/containers/run'


For debugging purposes, it can be useful to mount the file system of a container image.
This can be done with the following steps:

1. Create a buikdah unshare session with

   .. code-block:: bash

     buildah unshare

   This creates an environment where it looks like if you were root.
2. Create the ``bbuildah`` alias (the unshare environment does not know the alias yet, even if it was set in the shell where you executed ``buildah unshare``).
3. Create a working container from the desired image with

   .. code-block:: bash

     newontainer=$(bbuildah from <image_id>)

   This command will print a container id.
4. Mount the working container (identified by the id you got from the step before) with

   .. code-block:: bash

     containermnt=$(bbuildah mount $newcontainer)

   Container's file system is now available at ``$containermnt``.
5. After you are done, unmount the container's file system with

   .. code-block:: bash

     bbuildah umount $newcontainer

6. Delete the working container with

   .. code-block:: bash

     bbuildah rm $newcontainer

7. Exit the buildah unshare session by typing ``exit``

Alternatively, you can spawn a shell (e.g., bash) in the container by executing the following command after step 3:

.. code-block:: bash

  bbuildah run $newcontainer bash

Depending on your concrete setup, it might not be necessary to do this in an buildah unshare session.
