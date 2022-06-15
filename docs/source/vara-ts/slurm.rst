Running with Slurm
==================

This page describes how benchbuild/VaRA experiments can be run on the chair's cluster using slurm.

1. As no home directories are available on the cluster nodes, you must use ``scratch`` instead.
   Set up VaRA-TS as described :ref:`here<Installing VaRA Tool-Suite>` and make sure that the venv and the tool suite's install location are located under ``/scratch/<username>``.

   This guide assumes that your VaRA-TS root directory is ``/scratch/<user>/varats``:

   .. code-block:: bash

      VARATS_ROOT=/scratch/<user>/varats
      cd $VARATS_ROOT

2. Set slurm related parameters in the benchbuild config (``$VARATS_ROOT/benchbuild/.benchbuild.yml``) as needed:

   .. code-block:: yaml

      jobs: '20'
      parallel_processes: '1'

      slurm:
          account:
              value: ls-apel
          partition:
              value: anywhere # or name of the cluster to run on
          timelimit:
              value: 'hh:mm:ss'

3. Generate bb script

    .. note::

      Activate your virtualenv to use the correct benchbuild

   .. code-block:: bash

      vara-run --slurm -E <report_type> <project>

   The slurm script is generated as ``$VARATS_ROOT/benchbuild/<report_type>-slurm.sh``.
   If you want to keep multiple slurm scripts you should move the generated script to an appropriate subdirectory to avoid it getting overwritten, e.g.:

   .. code-block:: bash

      mv benchbuild/<report_type>-slurm.sh benchbuild/bb-configs/<report_type>-slurm-<project>.sh

4. (Optional) Modify -o parameter of SBATCH to get output file for debugging, e.g.

   .. code-block:: bash

      #SBATCH -o /scratch/<user>/varats/benchbuild/slurm-output/gravity/GenerateBlameReport-%A_%a.txt

5. Start a job:

   .. code-block:: bash

      cd benchbuild

      sbatch bb-configs/<report_type>-slurm-<project>.sh
      # or
      sbatch --constraint=kine bb-configs/<report_type>-slurm-<project>.sh

   You can also add the flag ``--submit`` to the ``vara-run`` command to directly submit the script to slurm.

.. tip::

  In case you get strange errors or results, try emptying all temporary directories and try again, e.g.:

      - ``$VARATS_ROOT/benchbuild/BC_files``
      - ``$VARATS_ROOT/benchbuild/results``
      - ``$VARATS_ROOT/benchbuild/tmp_dir``
      - ``$VARATS_ROOT/data_cache``


Handling Missing Dependencies for VaRA
--------------------------------------

.. note::

  The recommended way to run experiments requiring VaRA (or other complex research tools) is running them in a container as described in the next section and in our :ref:`container guide<Container Guide>`.

If certain libraries needed by VaRA or clang are missing on the slurm nodes, you can bring them yourself:

1. Create a folder for the libraries on scratch

   .. code-block:: bash

      mkdir /scratch/<username>/varats/libs

2. Copy the necessary libraries from your system to the libs folder

3. Add the following entry to the ``env`` section of your benchbuild config:

   .. code-block:: yaml

      env:
          value:
              LD_LIBRARY_PATH:
              - /scratch/<user>/varats/libs


Slurm and Container
-------------------

If you plan to use containers in combination with slurm, we suggest you first get familiar with our :ref:`container guide<Container Guide>` and our more detailed :ref:`BenchBuild container documentation <Running BenchBuild in a Container>`.
If you understand how BenchBuild uses containers to run experiments you can prepare your setup:

1. Set up VaRA-TS as described in the normal :ref:`slurm guide <Running with Slurm>` (steps 1 and 2).

2. Set up the BenchBuild container support as described in the :ref:`BenchBuild container documentation <Running BenchBuild in a Container>`.

3. Make sure that also the slurm cluster has rootless buildah and podman installed and configured (don't forget the subuid and subgid mappings for the users submitting the slurm jobs).

4. Preparing the research tool(s) for each base container required by your experiments, e.g.:

  .. code-block:: console

       vara-buildsetup build vara --container=DEBIAN_10

5. Rootless containers do not work on NFS (see `here <https://github.com/containers/podman/blob/master/rootless.md>`_), so we have to take some extra steps if we want to run containers via slurm.
   These steps can be executed easily using the following command (:ref:`documentation <vara-container>`):

   .. code-block:: bash

     vara-container prepare-slurm

   This step also builds the base images.

   If you want to know in detail what happens in this command, take a look at the section :ref:`Prepare-Slurm in Detail`.

6. After the preparation is complete, you can generate the slurm script as follows:

   .. code-block:: bash

     vara-run --slurm --container -E <report_type> <projects>

7. That's it! the script obtained from the previous step can be used like any other slurm script.
   You can now make any adjustments to the script if needed or just submit it to slurm as described in the slurm guide (step 5).
   You can also add the flag ``--submit`` to the ``vara-run`` command to directly submit the script to slurm.


Prepare-Slurm in Detail
...........................

As explained above, rootless containers do not work on NFS (see `here <https://github.com/containers/podman/blob/master/rootless.md>`_), so we have to take some extra steps if we want to run containers via slurm.
The recommended way to do this is using the ``vara-container prepare-slurm`` command, but in some situations it might be handy to know what happens under the hood:

    - You need to set the container root and runroot paths to some location that is not on a NFS, e.g., to a directory in ``tmp``:

      .. code-block:: yaml

        container:
          root:
            value: /tmp/<username>/containers/lib
          runroot:
            value: /tmp/<username>/containers/run

    - BenchBuild allows to export and import container images.
      That means that you can build the base images once, e.g., on your local machine, and export them so that the cluster nodes do not need to rebuild them over and over again.
      You can set the export and import paths in the BenchBuild config to point to some location both you and the slurm nodes have access (this path may be on a NFS):

      .. code-block:: yaml

        container:
          export:
            value: /scratch/<username>/varats/containers/export
          import:
            value: /scratch/<username>/varats/containers/export

      You then need to generate the base images like this:

      .. code-block:: bash

        vara-container build --export

      The ``--export`` option causes the created images to also be exported to the specified export path.

    - Set the slurm node directory in the Benchbuild config:

      .. code-block:: yaml

        slurm:
          node_dir:
            value: /tmp/<username>

      The node directory is the working directory on the slurm node.
      It acts as your home directory, i.e., ``HOME`` (and some other environment variables) will point to this directory during the runtime of the slurm job.
      To make containers work with slurm, this directory must not be on a NFS and the path must be relatively short due to Linux socket name length restrictions.
      This directory will be created and deleted by the slurm script generated by BenchBuild.
      Using some subdir of ``tmp`` is a good choice here.

    - Now it is time to generate the slurm script (cf. step 5 of the slurm guide).
      Because of our NFS workarounds, we cannot use the default script provided by BenchBuild, but we need to provide our own script template.
      You can find our default template in the ``varats.tools`` module.
      This template is very similar to the original template provided by BenchBuild, but it takes care of pointing all relevant environment variables to the slurm node directory as described in the points above.
      To activate the template, simply save it to the ``/scratch/<username>/varats/benchbuild`` directory and set the appropriate value in the BenchBuild config:

      .. code-block:: yaml

        slurm:
          template:
            value: /scratch/<username>/varats/benchbuild/slurm_container.sh.inc

      You can now continue with generating the slurm script as described above.
