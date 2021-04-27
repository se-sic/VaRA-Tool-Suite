Running with Slurm
==================

This page describes how benchbuild/VaRA experiments can be run on the chair's cluster using slurm.

As no home directories are available on the cluster nodes, you must use ``scratch`` instead.
Setup up a ``virtualenv`` with the tool suite in ``scratch/<user>``.

.. code-block:: bash

  cd /scratch/<user>/
  virtualenv -p /usr/bin/python3 vara-virt

Furthermore, this guide assumes that your vara-root directory is ``/scratch/<user>/varats``.

.. code-block:: bash

   cd /scratch/<user>/varats

1. Clone Tool-Suite and set up VaRA

   We assume that VaRA is installed to ``/scratch/<user>/varats/tools/VaRA``

2. Edit ``.varats.yaml`` and set options:

.. code-block:: yaml

   - result_dir: /scratch/<user>/varats/results
   - paper_config:
     - current_config: <your_config>
     - folder: /scratch/<user>/varats/paper_configs

3. Create benchbuild config (``vara-gen-bbconfig``)

4. Edit benchbuild config (``/scratch/<user>/varats/benchbuild/.benchbuild.yml``) as needed:

   - set benchbuild directories to point to scratch:

   .. code-block:: yaml

      build_dir:
         value: /scratch/<user>/varats/benchbuild/results
      tmp_dir:
         value: /scratch/<user>/varats/benchbuild/tmp

   - set environment variables to point to scratch:

   .. code-block:: yaml

      env:
        value:
            PATH:
            - /scratch/<user>/varats/tools/VaRA/bin/
            HOME: /scratch/<user>/

   - configure slurm related parameters:

   .. code-block:: yaml

      jobs: '10' # TODO: find good default
      parallel_processes: '4' # TODO: find good default

      slurm:
          account:
              value: ls-apel
          partition:
              value: anywhere # or name of the cluster to run on
          timelimit:
              value: 'hh:mm:ss'

   - set vara related options:

   .. code-block:: yaml

      vara:
          outfile: /scratch/<user>/varats/results
          result: BC_files

   - increase verbosity

   .. code-block:: yaml

      verbosity:
        value: <0-4>

5. Generate bb script

    .. note::

      Activate your virtualenv to use the correct benchbuild

   .. code-block:: bash

      benchbuild slurm -E <report_type> <project>

   Move resulting script to appropriate subdir, e.g.:

   .. code-block:: bash

      mv <report_type>-slurm.sh bb-configs/<report_type>-slurm-<project>.sh

6. (Optional) Modify -o parameter of SBATCH to get output file for debugging, e.g.

   .. code-block:: bash

      #SBATCH -o /scratch/<user>/varats/benchbuild/slurm-output/gravity/GenerateBlameReport-%A_%a.txt

7. Start a job:

   .. code-block:: bash

      cd benchbuild

      sbatch bb-configs/<report_type>-slurm-<project>.sh
      # or
      sbatch --constraint=kine bb-configs/<report_type>-slurm-<project>.sh

NOTE: If you want to run the same project again (with GenerateBlameReport), you need to empty the BC_files directory, because the path to the git repository will be different. See `#494 <https://github.com/se-passau/VaRA/issues/494>`_

To use interaction filters, we recommend storing all of them in a separate directory (e.g., benchbuild/interaction_filters) with descriptive names and symlinking them to the place where the experiment expects them.

TIP: In case you get strange errors or results, try to empty all temporary directories and try again, e.g.:

      - benchbuild/BC_files
      - benchbuild/results
      - benchbuild/tmp_dir
      - data_cache

Handling Missing Dependencies for VaRA
--------------------------------------

If certain libraries needed by vara or clang are missing on the slurm-nodes, you can bring them yourself:

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

If you are using containers, ``vara-container create`` will detect if such a entry in the BenchBuild config exists, copy all files found in this path into the container, and set the ``LD_LIBRARY_PATH`` inside the container appropriately.


Slurm and Container
-------------------

If you plan to use containers in combination with slurm, we suggest you first get familiar with our :ref:`BenchBuild container guide <Running BenchBuild in a Container>`.
If you understand how BenchBuild uses containers to run experiments you can prepare your setup:

1. Setup VaRA-TS as described in the normal :ref:`slurm guide <Running with Slurm>`.
   We will make some adjustments to the configuration later.

2. Setup the BenchBuild container support as described in the normal :ref:`container guide <Running BenchBuild in a Container>`.
   We will make some adjustments to this configuration later.

3. Make sure that also the slurm cluster has rootless buildah and podman installed and configured (don't forget the subuid and subgid mappings for the users submitting the slurm jobs).

4. Rootless containers do not work on NFS (see `here <https://github.com/containers/podman/blob/master/rootless.md>`_), so we have to take some extra steps if we want to run containers via slurm:

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
      You can download the template :download:`here <slurm_container.sh.inc>`.
      This template is very similar to the original template provided by BenchBuild, but it takes care of pointing all relevant environment variables to the slurm node directory as described in the points above.
      To activate the template, simply save it to the ``/scratch/<username>/varats/benchbuild`` directory and set the appropriate value in the BenchBuild config:

      .. code-block:: yaml

        slurm:
          template:
            value: /scratch/<username>/varats/benchbuild/slurm_container.sh.inc

      You can now generate the slurm script:

      .. code-block:: bash

        benchbuild slurm -S container run --import -E <report_type> <project>

      The additional ``-S container run --import`` tells BenchBuild to use the ``container run`` command in the script instead of the default ``run`` command.
      The ``--import`` is actually a parameter for the ``container`` command and specifies that we want to import container images from the path specified a couple of steps above if possible.

5. That's it! the script obtained from the previous step can be used like any other slurm script.
   You can now make any adjustments to the script if needed or just submit it to slurm as described in the slurm guide.
